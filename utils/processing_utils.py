import asyncio
import tiktoken
from typing import List, Optional, Tuple, Dict, Any
import aiohttp
from datetime import datetime

from utils.prompts import (
    email_summary_prompt,
    chunk_summary_prompt,
    combine_summaries_prompt
)
from utils.openrouter_utils import make_api_call
from utils.upload_to_cloudflare import CloudflareUploader
from utils.pinecone_utils import PineconeManager

# Initialize tokenizer
TOKENIZER = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
MAX_CHUNK_TOKENS = 190000  # Leave room for prompt tokens


class ProcessingManager:
    def __init__(self, requests_per_second: int = 100):
        """Initialize the processing manager with rate limiting."""
        self.semaphore = asyncio.Semaphore(requests_per_second)
        self.cloudflare = CloudflareUploader()
        self.pinecone = PineconeManager()
        self.session = None

    async def __aenter__(self):
        """Set up async context manager."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async context manager."""
        if self.session:
            await self.session.close()

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        return len(TOKENIZER.encode(text))

    def split_into_chunks(self, text: str, max_tokens: int = MAX_CHUNK_TOKENS) -> List[str]:
        """Split text into chunks that don't exceed token limit."""
        chunks = []
        current_chunk = []
        current_length = 0

        # Split into paragraphs
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            paragraph_tokens = self.count_tokens(paragraph)

            if current_length + paragraph_tokens <= max_tokens:
                current_chunk.append(paragraph)
                current_length += paragraph_tokens
            else:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                # Start new chunk with current paragraph
                current_chunk = [paragraph]
                current_length = paragraph_tokens

        # Add the last chunk if it exists
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def split_thread_by_tokens(self, thread_content: str, thread_id: str) -> List[Dict[str, Any]]:
        """
        Split thread content into chunks based on token count.
        Returns list of chunks with metadata.
        """
        chunks = self.split_into_chunks(thread_content)
        chunk_data = []

        for i, chunk in enumerate(chunks, 1):
            chunk_metadata = {
                "thread_id": thread_id,
                "chunk_number": i,
                "total_chunks": len(chunks),
                "is_chunked": len(chunks) > 1,
                "token_count": self.count_tokens(chunk)
            }
            chunk_data.append({
                "content": chunk,
                "metadata": chunk_metadata
            })

        return chunk_data

    async def rate_limited_api_call(self, *args, **kwargs):
        """Make an API call with rate limiting."""
        async with self.semaphore:
            return await make_api_call(*args, session=self.session, **kwargs)

    async def summarize_chunk(self, content: str, chunk_number: int, total_chunks: int) -> str:
        """Summarize a single chunk of content."""
        prompt = chunk_summary_prompt.format(
            content=content,
            chunk_number=chunk_number,
            total_chunks=total_chunks
        )
        return await self.rate_limited_api_call(prompt)

    async def combine_chunk_summaries(self, summaries: List[str]) -> str:
        """Combine multiple chunk summaries into one coherent summary."""
        formatted_summaries = "\n\n=== Part {} ===\n{}".format
        combined_text = "\n\n".join(
            formatted_summaries(i+1, summary)
            for i, summary in enumerate(summaries)
        )

        prompt = combine_summaries_prompt.format(summaries=combined_text)
        return await self.rate_limited_api_call(prompt)

    async def create_summary(self, content: str) -> str:
        """Create a summary of the content, handling large content appropriately."""
        content_tokens = self.count_tokens(content)

        if content_tokens <= MAX_CHUNK_TOKENS:
            # For content within token limit, create single summary
            prompt = email_summary_prompt.format(content=content)
            return await self.rate_limited_api_call(prompt)
        else:
            # For content exceeding token limit, split and summarize in chunks
            chunks = self.split_into_chunks(content)
            chunk_summaries = []

            # Summarize each chunk
            for i, chunk in enumerate(chunks, 1):
                summary = await self.summarize_chunk(chunk, i, len(chunks))
                chunk_summaries.append(summary)

            # Combine chunk summaries
            return await self.combine_chunk_summaries(chunk_summaries)

    async def process_thread(self, thread_id: str, content: str) -> Dict[str, Any]:
        """Process a single email thread completely."""
        try:
            # Check if content needs to be chunked
            content_tokens = self.count_tokens(content)
            if content_tokens > MAX_CHUNK_TOKENS:
                # Split into chunks
                chunks = self.split_thread_by_tokens(content, thread_id)
                results = []

                for chunk in chunks:
                    # Create summary for chunk
                    summary = await self.create_summary(chunk["content"])

                    # Upload chunk content to Cloudflare
                    chunk_filename = f"thread_{thread_id}_part{chunk['metadata']['chunk_number']}.txt"
                    cloudflare_path, metadata = await asyncio.to_thread(
                        self.cloudflare.upload_content,
                        chunk["content"],
                        chunk_filename,
                        chunk["metadata"]
                    )

                    if not cloudflare_path:
                        raise Exception(
                            f"Failed to upload chunk {chunk['metadata']['chunk_number']} of thread {thread_id} to Cloudflare")

                    # Create embedding of summary
                    vector_values = await asyncio.to_thread(
                        self.pinecone.create_embedding,
                        summary
                    )

                    # Upload to Pinecone with metadata
                    chunk_id = f"{thread_id}_part{chunk['metadata']['chunk_number']}"
                    success = await asyncio.to_thread(
                        self.pinecone.upsert_vector,
                        chunk_id,
                        vector_values,
                        {
                            "summary": summary,
                            "cloudflare_path": cloudflare_path,
                            "thread_id": thread_id,
                            "processed_date": datetime.utcnow().isoformat(),
                            **chunk["metadata"],
                            **metadata
                        }
                    )

                    if not success:
                        raise Exception(
                            f"Failed to upload chunk {chunk['metadata']['chunk_number']} of thread {thread_id} to Pinecone")

                    results.append({
                        "thread_id": thread_id,
                        "chunk_id": chunk_id,
                        "summary": summary,
                        "cloudflare_path": cloudflare_path,
                        **chunk["metadata"]
                    })

                # Return first chunk's data for compatibility
                return results[0]

            else:
                # Process as single chunk
                # Create summary
                summary = await self.create_summary(content)

                # Upload raw content to Cloudflare
                cloudflare_path, metadata = await asyncio.to_thread(
                    self.cloudflare.upload_content,
                    content,
                    f"thread_{thread_id}.txt",
                    {"thread_id": thread_id}
                )

                if not cloudflare_path:
                    raise Exception(
                        f"Failed to upload thread {thread_id} to Cloudflare")

                # Create embedding of summary
                vector_values = await asyncio.to_thread(
                    self.pinecone.create_embedding,
                    summary
                )

                # Upload to Pinecone with metadata
                success = await asyncio.to_thread(
                    self.pinecone.upsert_vector,
                    thread_id,
                    vector_values,
                    {
                        "summary": summary,
                        "cloudflare_path": cloudflare_path,
                        "thread_id": thread_id,
                        "processed_date": datetime.utcnow().isoformat(),
                        "is_chunked": False,
                        **metadata
                    }
                )

                if not success:
                    raise Exception(
                        f"Failed to upload thread {thread_id} to Pinecone")

                return {
                    "thread_id": thread_id,
                    "summary": summary,
                    "cloudflare_path": cloudflare_path,
                    "is_chunked": False
                }

        except Exception as e:
            print(f"Error processing thread {thread_id}: {str(e)}")
            return None


async def process_threads(thread_ids: List[str]) -> List[Dict[str, Any]]:
    """Process multiple threads in parallel with rate limiting."""
    async with ProcessingManager() as manager:
        tasks = []
        for thread_id in thread_ids:
            # Read the thread content
            try:
                with open(f"data/test_emails/{thread_id}.txt", 'r') as f:
                    content = f.read()

                task = asyncio.create_task(
                    manager.process_thread(thread_id, content)
                )
                tasks.append(task)
            except Exception as e:
                print(f"Error reading thread {thread_id}: {str(e)}")
                continue

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        return [r for r in results if r is not None and not isinstance(r, Exception)]

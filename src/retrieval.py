#!/usr/bin/env python3
from utils.pinecone_utils import PineconeManager
from utils.openrouter_utils import make_api_call
import asyncio
from typing import List, Dict, Optional
import aiohttp
import sys
from pathlib import Path
import os

# Add parent directory to Python path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import after adding to path


class QueryProcessor:
    def __init__(self):
        """Initialize the query processor with required components."""
        self.pinecone = PineconeManager()

    async def refine_query(self, initial_query: str) -> str:
        """
        Interactively refine the user's query through a chatbot conversation.
        Returns an enhanced, more comprehensive query.
        """
        # Initial prompt to analyze and expand the query
        refinement_prompt = f"""You are an expert information retrieval specialist. 
Given this initial query: "{initial_query}"
Ask 2-3 clarifying questions that would help understand exactly what information the user needs.
Format your response as a simple list of questions, with no additional text.
"""
        try:
            # Get clarifying questions
            questions = await make_api_call(refinement_prompt, model="openai/o3-mini")
            print("\nTo better understand your needs, please answer these questions:")
            print(questions)

            # Collect user responses
            print(
                "\nPlease provide your answers (one per line, press Enter twice when done):")
            responses = []
            while True:
                line = input()
                if not line:
                    break
                responses.append(line)

            # Generate enhanced query
            enhancement_prompt = f"""Based on the initial query and user responses, create a comprehensive search query that captures all relevant aspects.
Initial query: {initial_query}
User responses:
{chr(10).join(responses)}

Create a detailed, standalone query that incorporates all this information:"""

            enhanced_query = await make_api_call(enhancement_prompt, model="openai/o3-mini")
            print(f"\nEnhanced query: {enhanced_query}")
            return enhanced_query

        except Exception as e:
            print(f"Error refining query: {str(e)}")
            return initial_query

    async def check_relevance(self, query: str, summary: str, score: float, session: aiohttp.ClientSession) -> bool:
        """
        Check if a document summary is relevant to the query using vector similarity score
        and O3 mini model for verification.
        """
        print(f"\nChecking relevance for document with score {score}")
        print(f"Summary preview: {summary[:100]}...")

        # Lower the high confidence threshold to be more inclusive
        if score > 0.5:  # Changed from 0.7 to 0.5
            print(f"Document accepted based on good similarity score: {score}")
            return True

        # For lower scores, use O3 mini to verify relevance
        relevance_prompt = f"""Given this query: "{query}"
And this email summary: "{summary}"
Determine if this email could contain ANY information relevant to the query.
Consider ANY potential connection or related information as relevant.
Even if the connection seems indirect, if it might be useful, consider it relevant.
Answer with ONLY 'yes' or 'no':"""

        try:
            result = await make_api_call(relevance_prompt, model="openai/o3-mini", session=session)
            is_relevant = result.lower().strip() == 'yes'
            print(f"O3 relevance check result: {is_relevant}")
            return is_relevant
        except Exception as e:
            print(f"Error checking relevance: {str(e)}")
            # Be more lenient - for lower scores, keep document if check fails
            return score > 0.3  # Changed from 0.5 to 0.3

    async def get_all_documents(self, query: str) -> List[Dict]:
        """Get potentially relevant documents from Pinecone."""
        try:
            # Get documents using query embedding
            docs = self.pinecone.get_all_documents(query)
            print(f"\nPinecone returned {len(docs)} documents")
            if docs:
                scores = [d['score'] for d in docs]
                print(f"Score range: {min(scores):.3f} to {max(scores):.3f}")
                print(f"Average score: {sum(scores)/len(scores):.3f}")
            return docs
        except Exception as e:
            print(f"Error getting documents: {str(e)}")
            return []

    async def screen_documents(self, query: str) -> List[Dict]:
        """
        Screen documents for relevance using vector similarity scores and O3 mini model.
        Uses exponential backoff and rate limiting for API calls.
        """
        try:
            # Get potentially relevant documents with similarity scores
            all_docs = await self.get_all_documents(query)
            if not all_docs:
                print("No documents found in database")
                return []

            print(f"\nScreening {len(all_docs)} documents...")

            # Screen each document with rate limiting
            semaphore = asyncio.Semaphore(100)  # Max 100 concurrent requests
            relevant_docs = []
            processed_count = 0
            openrouter_calls = 0

            async with aiohttp.ClientSession() as session:
                async def process_doc(doc):
                    nonlocal processed_count, openrouter_calls
                    async with semaphore:
                        processed_count += 1
                        is_relevant = await self.check_relevance(
                            query,
                            doc['summary'],
                            doc.get('score', 0),
                            session
                        )
                        # Only count OpenRouter calls for lower scores
                        if not doc.get('score', 0) > 0.5:
                            openrouter_calls += 1

                        if is_relevant:
                            relevant_docs.append({
                                'cloudflare_path': doc['cloudflare_path'],
                                'summary': doc['summary'],
                                'score': doc.get('score', 0)
                            })
                        print(
                            f"\rProcessed {processed_count}/{len(all_docs)} documents", end="")

                # Create tasks for all documents
                tasks = [process_doc(doc) for doc in all_docs]
                await asyncio.gather(*tasks)
                print(
                    f"\nMade {openrouter_calls} OpenRouter API calls for relevance checks")

            print(f"\nFound {len(relevant_docs)} relevant documents")
            if relevant_docs:
                scores = [d['score'] for d in relevant_docs]
                print(
                    f"Relevant docs score range: {min(scores):.3f} to {max(scores):.3f}")
                print(
                    f"Relevant docs average score: {sum(scores)/len(scores):.3f}")

            return relevant_docs

        except Exception as e:
            print(f"Error screening documents: {str(e)}")
            return []


async def search_emails(query: str, skip_refinement: bool = False) -> None:
    """
    Main function to search emails with query refinement and screening.

    Args:
        query: The search query
        skip_refinement: If True, skips interactive query refinement (useful for testing)
    """
    try:
        processor = QueryProcessor()

        if skip_refinement:
            enhanced_query = query
        else:
            # Refine the query
            print("\nLet's refine your search query to get the best results.")
            enhanced_query = await processor.refine_query(query)

        # Screen documents
        print("\nSearching for relevant emails...")
        relevant_docs = await processor.screen_documents(enhanced_query)

        if not relevant_docs:
            print("\nNo relevant emails found.")
            return

        # Display results
        print(f"\nFound {len(relevant_docs)} relevant emails:")
        for i, doc in enumerate(relevant_docs, 1):
            print(f"\n{i}. Document Link: {doc['cloudflare_path']}")
            print(f"Score: {doc['score']:.3f}")
            print("Summary:")
            print(doc['summary'][:300] + "..." if len(doc['summary'])
                  > 300 else doc['summary'])
            print("-" * 80)

    except Exception as e:
        print(f"Error searching emails: {str(e)}")


async def main():
    """CLI interface for email search."""
    print("Email Search System")
    print("Enter your search query:")
    query = input().strip()

    if query:
        await search_emails(query)
    else:
        print("No query provided.")

if __name__ == "__main__":
    asyncio.run(main())

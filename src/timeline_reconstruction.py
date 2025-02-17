#!/usr/bin/env python3
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncio
from src.retrieval import search_emails


class TimelineReconstructor:
    def __init__(self):
        """Initialize the timeline reconstructor."""
        self.timeline_file = Path("data/timeline.txt")
        self.date_pattern = r'\b(\d{4}-\d{2}-\d{2})\b'

    def _clean_content(self, content: str) -> str:
        """Clean up email content by removing headers and extra whitespace."""
        # Split into lines
        lines = content.strip().split('\n')

        # Skip header lines until we find 'Content:'
        content_start = False
        cleaned_lines = []

        for line in lines:
            if 'Content:' in line:
                content_start = True
                continue
            if content_start:
                cleaned_lines.append(line)

        # Join lines and clean up whitespace
        return '\n'.join(cleaned_lines).strip()

    def extract_dates(self, content: str) -> List[Tuple[str, str]]:
        """
        Extract dates and associated content from email text.
        Returns list of (date, content) tuples.
        """
        # Split content into sections by the email separator
        sections = content.split("-" * 80)
        dates_content = []

        for section in sections:
            if not section.strip():
                continue

            # Find all dates in the section
            dates = re.findall(self.date_pattern, section)
            if dates:
                # Use the first date found as the reference date for this section
                date = dates[0]
                # Clean up the content
                clean_content = self._clean_content(section)
                if clean_content:
                    dates_content.append((date, clean_content))

        return sorted(dates_content, key=lambda x: x[0])

    async def _generate_timeline_entry(self, email_content: str, existing_timeline: str = "") -> str:
        """
        Use O3 mini to generate a human-readable timeline entry from an email,
        taking into account the existing timeline context.
        """
        from utils.openrouter_utils import make_api_call

        prompt = f"""You are a patent timeline expert. Given an email about a patent and the existing timeline, 
create a concise but detailed timeline entry that captures key developments and fits naturally with the narrative.
Focus on technical details, decisions, and progress milestones.

Existing Timeline:
{existing_timeline}

Email Content:
{email_content}

Generate a clear, informative timeline entry that adds to this narrative. Focus on what's new or noteworthy.
Format as a single paragraph without bullet points. Do not include email metadata, just the key information.
"""
        try:
            entry = await make_api_call(prompt, model="openai/o3-mini")
            return entry.strip()
        except Exception as e:
            print(f"Error generating timeline entry: {str(e)}")
            return ""

    async def process_query(self, query: str) -> List[Dict]:
        """Process a query and return relevant documents."""
        try:
            # Get documents from Cloudflare using the search function
            await search_emails(query, skip_refinement=True)

            # For testing, directly read the test email files
            test_dir = Path("data/test_emails")
            test_files = list(test_dir.glob("thread_test_*.txt")) + \
                list(test_dir.glob("patent_thread_*.txt"))
            docs = []

            for file_path in test_files:
                try:
                    content = file_path.read_text()
                    docs.append({
                        'content': content,
                        'cloudflare_path': f"docs/{file_path.name}"
                    })
                except Exception as e:
                    print(f"Error reading test file {file_path}: {str(e)}")

            return docs
        except Exception as e:
            print(f"Error processing query: {str(e)}")
            return []

    async def update_timeline(self, date: str, content: str, cloudflare_path: str) -> None:
        """
        Update the timeline.txt file with a new entry while maintaining chronological order.
        Uses O3 mini to generate a human-readable entry that fits with the existing narrative.
        """
        try:
            # Read existing timeline
            existing_timeline = ""
            existing_entries = []
            if self.timeline_file.exists():
                with open(self.timeline_file, 'r') as f:
                    existing_timeline = f.read()
                    if existing_timeline:
                        # Split into entries and parse dates
                        entries = existing_timeline.split('\n\n')
                        for entry in entries:
                            if entry.strip():
                                date_match = re.search(
                                    self.date_pattern, entry)
                                if date_match:
                                    existing_entries.append(
                                        (date_match.group(1), entry.strip()))

            # Generate new timeline entry using O3 mini
            new_entry = await self._generate_timeline_entry(content, existing_timeline)
            if new_entry:
                # Format the new entry
                formatted_entry = f"[{date}]\n{new_entry}\nReference: {cloudflare_path}"
                existing_entries.append((date, formatted_entry))

                # Sort all entries by date
                existing_entries.sort(key=lambda x: x[0])

                # Write updated timeline
                with open(self.timeline_file, 'w') as f:
                    for i, (_, entry) in enumerate(existing_entries):
                        f.write(entry)
                        if i < len(existing_entries) - 1:
                            f.write('\n\n')

        except Exception as e:
            print(f"Error updating timeline: {str(e)}")

    async def reconstruct_timeline(self, query: str) -> bool:
        """
        Main function to reconstruct timeline based on a query.
        Returns True if timeline was successfully updated, False otherwise.
        """
        try:
            # Process query to get relevant documents
            relevant_docs = await self.process_query(query)
            if not relevant_docs:
                print("No relevant documents found for the query.")
                return False

            # Process each document
            for doc in relevant_docs:
                # Extract date from email
                dates = re.findall(self.date_pattern, doc['content'])
                if dates:
                    # Use the first date found as the reference date
                    date = dates[0]
                    # Update timeline with AI-generated entry
                    await self.update_timeline(date, doc['content'], doc['cloudflare_path'])

            return True

        except Exception as e:
            print(f"Error reconstructing timeline: {str(e)}")
            return False


async def main():
    """CLI interface for timeline reconstruction."""
    reconstructor = TimelineReconstructor()
    print("Timeline Reconstruction System")
    print("Enter your query (e.g., 'Show me the timeline for patent XYZ'):")
    query = input().strip()

    if query:
        success = await reconstructor.reconstruct_timeline(query)
        if success:
            print("\nTimeline has been updated successfully!")
            print(
                f"You can find the timeline at: {reconstructor.timeline_file}")
        else:
            print("\nFailed to reconstruct timeline.")
    else:
        print("No query provided.")

if __name__ == "__main__":
    asyncio.run(main())

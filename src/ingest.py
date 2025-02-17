#!/usr/bin/env python3
from src.directory_manager import ensure_directories
from src.thread_processor import process_thread, save_thread
from src.email_fetcher import get_email_threads, validate_thread
from utils.processing_utils import process_threads
from utils.gmail_auth import get_gmail_service
import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


async def process_email_pipeline(service, test_mode: bool = False) -> List[Dict]:
    """
    Main email processing pipeline.
    Returns list of successfully processed thread results.
    """
    try:
        # Get email threads
        print("Fetching email threads...")
        threads = await get_email_threads(service, test_mode)

        if not threads:
            print("No threads found.")
            return []

        print(f"Found {len(threads)} threads to process")

        # First phase: Download and save threads
        thread_ids = []
        for i, thread in enumerate(threads, 1):
            if not validate_thread(thread):
                print(f"Skipping invalid thread {thread.get('id', 'unknown')}")
                continue

            thread_id = thread["id"]
            print(f"\nProcessing thread {i}/{len(threads)} (ID: {thread_id})")

            # Process thread
            content = await process_thread(service, thread)
            if content:
                # Save thread
                await save_thread(content, thread_id)
                thread_ids.append(thread_id)
                print(f"Saved thread {thread_id}")
            else:
                print(f"Failed to process thread {thread_id}")

        # Second phase: Process saved threads (summarize, upload, index)
        print("\nProcessing saved threads...")
        results = await process_threads(thread_ids)

        # Print processing results
        print("\nProcessing Results:")
        for result in results:
            print(f"Thread {result['thread_id']}:")
            print(f"  - Cloudflare path: {result['cloudflare_path']}")
            print(f"  - Summary length: {len(result['summary'])} chars")

        return results

    except Exception as e:
        print(f"Error in email pipeline: {str(e)}")
        return []


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Gmail Thread Ingestion Script")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (process last 7 days only)")
    return parser.parse_args()


async def main():
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_arguments()
        if args.test:
            print("Running in test mode - processing emails from last 7 days only")
        else:
            print("Running in full mode - processing all emails")

        # Change to project root directory
        os.chdir(project_root)

        # Ensure directories exist
        ensure_directories()

        # Initialize Gmail service
        service = get_gmail_service()

        # Run processing pipeline
        results = await process_email_pipeline(service, args.test)

        if results:
            print("\nEmail ingestion complete!")
            print(f"Successfully processed {len(results)} threads")
        else:
            print("\nNo threads were successfully processed")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
from src.retrieval import search_emails
import asyncio
import sys
from pathlib import Path

# Add parent directory to Python path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


async def run_test_queries():
    """Run test queries to verify the retrieval system."""
    test_queries = [
        "Information about ammonium sulphate",
        "HR meeting details",
        "Wedding information"
    ]

    print("Running test queries...")
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Testing query: {query}")
        print(f"{'='*80}\n")
        await search_emails(query, skip_refinement=True)
        print("\nMoving to next query...\n")
        await asyncio.sleep(1)  # Brief pause between queries for readability

if __name__ == "__main__":
    asyncio.run(run_test_queries())

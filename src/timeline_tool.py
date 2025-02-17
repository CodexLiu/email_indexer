#!/usr/bin/env python3
import asyncio
from pathlib import Path
from timeline_reconstruction import TimelineReconstructor
from retrieval import QueryProcessor
import sys


async def process_query(query: str):
    """Process a search query and generate a timeline."""
    print("\nProcessing query:", query)

    # Initialize processors
    query_processor = QueryProcessor()
    timeline_reconstructor = TimelineReconstructor()

    # Get relevant documents
    print("\nSearching for relevant documents...")
    relevant_docs = await query_processor.screen_documents(query)
    print(f"Found {len(relevant_docs)} relevant documents")

    # Reconstruct timeline
    print("\nReconstructing timeline...")
    success = await timeline_reconstructor.reconstruct_timeline(query)

    if success:
        print("\nTimeline generated successfully!")
        print(f"Timeline saved to: {timeline_reconstructor.timeline_file}")

        # Display the timeline
        if timeline_reconstructor.timeline_file.exists():
            print("\nGenerated Timeline:")
            print("=" * 80)
            print(timeline_reconstructor.timeline_file.read_text())
            print("=" * 80)
    else:
        print("\nFailed to generate timeline.")


async def main():
    """Main function to run the timeline tool."""
    print("Timeline Generation Tool")
    print("=" * 80)
    print("Enter your query (e.g., 'Show me the timeline for the enzyme patent')")
    print("Enter 'quit' to exit")
    print("=" * 80)

    while True:
        try:
            query = input("\nEnter query: ").strip()
            if query.lower() == 'quit':
                break

            if query:
                await process_query(query)
            else:
                print("Please enter a valid query")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error processing query: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

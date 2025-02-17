#!/usr/bin/env python3
from src.timeline_reconstruction import TimelineReconstructor
from utils.processing_utils import process_threads
from utils.upload_to_cloudflare import CloudflareUploader
import asyncio
from pathlib import Path
import sys
from typing import List, Dict

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


async def upload_test_emails() -> List[str]:
    """Upload test email threads to Cloudflare and return their IDs."""
    print("\nUploading test email threads...")
    thread_ids = []
    uploader = CloudflareUploader()

    # Get all test email files
    test_dir = Path("data/test_emails")
    test_files = list(test_dir.glob("patent_thread_*.txt"))

    for file_path in test_files:
        try:
            # Read the email content
            content = file_path.read_text()

            # Upload to Cloudflare
            thread_id = file_path.stem
            cloudflare_path, metadata = uploader.upload_content(
                content,
                f"{thread_id}.txt",
                {"thread_id": thread_id}
            )

            if cloudflare_path:
                print(f"✅ Uploaded {file_path.name}")
                thread_ids.append(thread_id)
            else:
                print(f"❌ Failed to upload {file_path.name}")

        except Exception as e:
            print(f"Error uploading {file_path.name}: {str(e)}")

    return thread_ids


async def process_test_threads(thread_ids: List[str]) -> List[Dict]:
    """Process uploaded test threads through the email pipeline."""
    print("\nProcessing test threads...")
    return await process_threads(thread_ids)


async def test_timeline_reconstruction():
    """Test the timeline reconstruction functionality."""
    try:
        # First, upload test emails
        thread_ids = await upload_test_emails()
        if not thread_ids:
            print("No test emails were uploaded successfully.")
            return

        # Process the uploaded threads
        results = await process_test_threads(thread_ids)
        if not results:
            print("No threads were processed successfully.")
            return

        print("\nTest threads uploaded and processed successfully!")

        # Now test timeline reconstruction
        print("\nTesting timeline reconstruction...")
        reconstructor = TimelineReconstructor()

        # Test with a specific query about the enzyme patent
        test_query = "Show me the timeline for our enzyme stabilization patent"
        print(f"\nExecuting test query: '{test_query}'")

        success = await reconstructor.reconstruct_timeline(test_query)

        if success:
            print("\nTimeline reconstruction successful!")
            print(f"Timeline file created at: {reconstructor.timeline_file}")

            # Display the timeline
            if reconstructor.timeline_file.exists():
                print("\nGenerated Timeline:")
                print("=" * 80)
                print(reconstructor.timeline_file.read_text())
                print("=" * 80)
        else:
            print("\nFailed to reconstruct timeline.")

    except Exception as e:
        print(f"Error in timeline reconstruction test: {str(e)}")


async def main():
    """Main test function."""
    print("Starting Timeline Reconstruction Test")
    await test_timeline_reconstruction()

if __name__ == "__main__":
    asyncio.run(main())

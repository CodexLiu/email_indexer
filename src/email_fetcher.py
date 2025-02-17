#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from googleapiclient.errors import HttpError

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


async def get_email_threads(service, test_mode=False) -> List[Dict]:
    """
    Fetch email threads from Gmail API.
    If test_mode is True, only fetch threads from the last 7 days.
    """
    try:
        # Calculate date for test mode
        if test_mode:
            seven_days_ago = (
                datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')
            query = f'after:{seven_days_ago}'
        else:
            query = None

        # Get list of all thread IDs
        threads_response = service.users().threads().list(
            userId="me",
            q=query
        ).execute()

        threads = threads_response.get('threads', [])

        # Fetch full thread data for each thread
        full_threads = []
        for thread in threads:
            try:
                full_thread = service.users().threads().get(
                    userId="me",
                    id=thread["id"],
                    format="full"
                ).execute()
                full_threads.append(full_thread)
            except Exception as e:
                print(f"Error fetching thread {thread['id']}: {str(e)}")
                continue

        return full_threads

    except HttpError as error:
        print(f'An error occurred fetching threads: {error}')
        return []


def get_thread_metadata(thread: Dict) -> Dict:
    """Extract and validate thread metadata."""
    metadata = {
        'thread_id': thread.get('id'),
        'history_id': thread.get('historyId'),
        'messages': len(thread.get('messages', [])),
        'snippet': thread.get('snippet', '')
    }
    return metadata


def validate_thread(thread: Dict) -> bool:
    """
    Validate thread data structure and required fields.
    Returns True if thread is valid, False otherwise.
    """
    if not thread:
        return False

    required_fields = ['id', 'messages']
    has_fields = all(field in thread for field in required_fields)
    has_messages = len(thread.get('messages', [])) > 0

    return has_fields and has_messages

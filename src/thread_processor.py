#!/usr/bin/env python3
from src.attachment_processor import process_attachment
from utils.gmail_auth import get_gmail_service
import sys
from pathlib import Path
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from googleapiclient.errors import HttpError

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


async def process_thread(service, thread: Dict) -> Optional[str]:
    """Process a single email thread and return formatted content."""
    try:
        thread_content = []

        # Process each message in thread
        for message in thread["messages"]:
            email_content = await process_message(message)
            if email_content:
                thread_content.append(email_content)
                # Message separator
                thread_content.append("\n" + "-"*80 + "\n")

        return "\n".join(thread_content) if thread_content else None

    except Exception as error:
        print(
            f"An error occurred processing thread {thread.get('id')}: {error}")
        return None


async def process_message(message: Dict[str, Any]) -> Optional[str]:
    """Process a single email message and return formatted content."""
    try:
        headers = extract_headers(message)
        content = []

        # Add metadata section
        content.extend([
            f"From: {headers.get('From', 'Unknown')}",
            f"To: {headers.get('To', 'Unknown')}",
            f"Date: {format_date(headers.get('Date', ''))}",
            f"Subject: {headers.get('Subject', 'No Subject')}",
            "\nContent:",
        ])

        # Process message parts
        message_parts = get_message_parts(message)
        for part in message_parts:
            part_content = await process_message_part(part, message["id"])
            if part_content:
                content.append(part_content)

        return "\n".join(content)

    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return None


def extract_headers(message: Dict[str, Any]) -> Dict[str, str]:
    """Extract and format email headers."""
    return {
        header["name"]: header["value"]
        for header in message["payload"]["headers"]
    }


def format_date(date_str: str) -> str:
    """Format date string to consistent format."""
    try:
        # Parse the email date format and convert to consistent format
        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return date_str


def get_message_parts(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get message parts, handling both multipart and single part messages."""
    if "parts" in message["payload"]:
        return message["payload"]["parts"]
    return [message["payload"]]


async def process_message_part(part: Dict[str, Any], message_id: str) -> Optional[str]:
    """Process a single message part and return its content."""
    try:
        if part["mimeType"] == "text/plain":
            return extract_text_content(part)

        elif part["mimeType"].startswith("multipart/"):
            return await process_multipart(part)

        elif "filename" in part and part["filename"]:
            return await process_attachment_part(part, message_id)

        return None

    except Exception as e:
        print(f"Error processing message part: {str(e)}")
        return None


def extract_text_content(part: Dict[str, Any]) -> Optional[str]:
    """Extract text content from a message part."""
    try:
        if "data" in part["body"]:
            return base64.urlsafe_b64decode(
                part["body"]["data"]).decode("utf-8")
        return None
    except Exception as e:
        print(f"Error extracting text content: {str(e)}")
        return None


async def process_multipart(part: Dict[str, Any]) -> Optional[str]:
    """Process multipart message content."""
    content = []
    for subpart in part.get("parts", []):
        if subpart["mimeType"] == "text/plain":
            text = extract_text_content(subpart)
            if text:
                content.append(text)
    return "\n".join(content) if content else None


async def process_attachment_part(part: Dict[str, Any], message_id: str) -> Optional[str]:
    """Process attachment part and return formatted content."""
    try:
        print(f"Processing attachment: {part['filename']}")
        part["messageId"] = message_id
        attachment_content = await process_attachment(part)

        if attachment_content:
            return "\n".join([
                "\n" + "="*50,
                f"ATTACHMENT: {part['filename']}",
                "="*50,
                attachment_content
            ])
        return None

    except Exception as e:
        print(f"Error processing attachment part: {str(e)}")
        return None


async def save_thread(thread_content: str, thread_id: str) -> None:
    """Save processed thread content to file."""
    output_path = Path("data/raw_emails") / f"thread_{thread_id}.txt"
    output_path.write_text(thread_content, encoding="utf-8")

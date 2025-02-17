#!/usr/bin/env python3
from utils.file_converter import convert_file_to_text
from utils.gmail_auth import get_gmail_service
import sys
from pathlib import Path
import base64
import os
import tempfile
from typing import Dict, Optional, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


async def process_attachment(attachment_data: Dict[str, Any]) -> Optional[str]:
    """Process a single attachment and return its transcribed content."""
    temp_path = None
    final_path = None

    try:
        attachment_data = await handle_attachment_data(attachment_data)
        if not attachment_data:
            return None

        temp_path = create_temp_file(attachment_data["file_data"])
        if not temp_path:
            return None

        final_path = add_extension_to_file(
            temp_path, attachment_data["mime_type"])
        if not final_path:
            cleanup_temp_files(temp_path)
            return None

        return await process_file_content(final_path)

    except Exception as e:
        print(f"Error processing attachment: {str(e)}")
        cleanup_files(temp_path, final_path)
        return None


async def handle_attachment_data(attachment_data: Dict[str, Any]) -> Optional[Dict]:
    """Extract and decode attachment data."""
    try:
        if "data" in attachment_data.get("body", {}):
            return {
                "file_data": base64.urlsafe_b64decode(
                    attachment_data["body"]["data"]),
                "mime_type": attachment_data["mimeType"]
            }

        attachment_id = attachment_data.get("body", {}).get("attachmentId")
        if attachment_id:
            service = get_gmail_service()
            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=attachment_data["messageId"],
                id=attachment_id
            ).execute()

            if "data" in attachment:
                return {
                    "file_data": base64.urlsafe_b64decode(attachment["data"]),
                    "mime_type": attachment_data["mimeType"]
                }

        print("No attachment data or ID found")
        return None

    except Exception as e:
        print(f"Error handling attachment data: {str(e)}")
        return None


def create_temp_file(file_data: bytes) -> Optional[str]:
    """Create a temporary file with the given data."""
    try:
        temp_dir = Path("data/processed/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as temp_file:
            temp_file.write(file_data)
            return temp_file.name

    except Exception as e:
        print(f"Error creating temp file: {str(e)}")
        return None


def add_extension_to_file(temp_path: str, mime_type: str) -> Optional[str]:
    """Add the appropriate extension to the temporary file."""
    extension = get_extension_for_mime_type(mime_type)
    if not extension:
        print(f"Unsupported mime type: {mime_type}")
        return None

    final_path = temp_path + extension
    try:
        os.rename(temp_path, final_path)
        return final_path
    except Exception as e:
        print(f"Error adding extension to file: {str(e)}")
        return None


def get_extension_for_mime_type(mime_type: str) -> Optional[str]:
    """Map MIME types to file extensions."""
    mime_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"
    }
    return mime_map.get(mime_type)


async def process_file_content(file_path: str) -> Optional[str]:
    """Process the file and extract its content."""
    try:
        return await convert_file_to_text(file_path)
    except Exception as e:
        print(f"Error processing file content: {str(e)}")
        return None


def cleanup_files(temp_path: Optional[str], final_path: Optional[str]) -> None:
    """Clean up temporary files."""
    if temp_path and os.path.exists(temp_path):
        os.unlink(temp_path)
    if final_path and final_path != temp_path and os.path.exists(final_path):
        os.unlink(final_path)

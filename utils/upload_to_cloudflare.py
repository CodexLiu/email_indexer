import boto3
from boto3.session import Session
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, Optional, Tuple

# Load environment variables
load_dotenv()


class CloudflareUploader:
    def __init__(self):
        """Initialize CloudflareUploader with credentials from environment."""
        self.endpoint = os.getenv('R2_ENDPOINT')
        self.access_key = os.getenv('R2_ACCESS_KEY_ID')
        self.secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME')

        if not all([self.endpoint, self.access_key, self.secret_key, self.bucket_name]):
            raise ValueError("Missing required Cloudflare R2 credentials")

        # Create S3 client
        self.session = Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='wnam'
        )

        self.s3 = self.session.client(
            's3',
            endpoint_url=self.endpoint
        )

    def upload_document(self, file_path: str, metadata: Dict = None) -> Tuple[Optional[str], Dict]:
        """
        Upload a document to Cloudflare R2.
        Returns tuple of (cloudflare_path, metadata) if successful, (None, {}) if failed.
        """
        try:
            # Generate timestamp for unique path
            timestamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M")

            # Create R2 path
            base_name = Path(file_path).name
            r2_path = f"docs/{timestamp}_{base_name}"

            # Upload file
            with open(file_path, 'rb') as f:
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=r2_path,
                    Body=f.read(),
                    Metadata=metadata or {}
                )

            print(f"✅ Upload successful: {r2_path}")

            # Return the path and metadata
            return r2_path, metadata or {}

        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            return None, {}

    def upload_content(self, content: str, filename: str, metadata: Dict = None) -> Tuple[Optional[str], Dict]:
        """
        Upload string content directly to Cloudflare R2.
        Returns tuple of (cloudflare_path, metadata) if successful, (None, {}) if failed.
        """
        try:
            # Generate timestamp for unique path
            timestamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M")

            # Create R2 path
            r2_path = f"docs/{timestamp}_{filename}"

            # Upload content
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=r2_path,
                Body=content.encode('utf-8'),
                Metadata=metadata or {}
            )

            print(f"✅ Upload successful: {r2_path}")

            # Return the path and metadata
            return r2_path, metadata or {}

        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            return None, {}

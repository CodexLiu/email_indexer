import boto3
from boto3.session import Session
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Debug: Print environment variables and their lengths
print("\nEnvironment variables and lengths:")
print(f"R2_ENDPOINT: {os.getenv('R2_ENDPOINT')}")
print(
    f"R2_ACCESS_KEY_ID: {os.getenv('R2_ACCESS_KEY_ID')} (length: {len(os.getenv('R2_ACCESS_KEY_ID'))})")
print(
    f"R2_SECRET_ACCESS_KEY: {os.getenv('R2_SECRET_ACCESS_KEY')[:10]}... (length: {len(os.getenv('R2_SECRET_ACCESS_KEY'))})")
print(f"R2_BUCKET_NAME: {os.getenv('R2_BUCKET_NAME')}")


def upload_test():
    """Test file upload to Cloudflare R2."""
    # Create test directory and file
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_upload.txt"
    test_content = "This is a test file for Cloudflare R2 upload."

    try:
        # Write test content
        test_file.write_text(test_content)
        print(f"Created test file: {test_file}")

        # Create session with explicit credentials
        session = Session(
            aws_access_key_id='9fe85ce0d2ae09f60cf4535c9c1535ac',
            aws_secret_access_key='cdb01b732d1ac833a3a097fdb08a504a0e87d362c4fd3fd86e147a3eda61ca05',
            region_name='wnam'
        )

        # Create S3 client from session
        s3 = session.client(
            's3',
            endpoint_url='https://a6de424a6ef28106be8cdb17bee186aa.r2.cloudflarestorage.com'
        )

        # Prepare upload details
        bucket = 'gmail-indexer'
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M")
        r2_path = f"docs/test_upload_{timestamp}.txt"

        # Upload file
        with open(test_file, 'rb') as f:
            s3.put_object(
                Bucket=bucket,
                Key=r2_path,
                Body=f.read()
            )

        print(f"✅ Upload successful: {r2_path}")

    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        if test_dir.exists():
            test_dir.rmdir()
        print("Test files cleaned up")


if __name__ == "__main__":
    upload_test()

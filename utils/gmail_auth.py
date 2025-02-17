import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # Read, compose, and send
    "https://www.googleapis.com/auth/gmail.send"     # Send-only permission
]


def get_gmail_service():
    """
    Handles Gmail API authentication and returns the service object.

    Returns:
        service: Authenticated Gmail API service instance

    Raises:
        Exception: If authentication fails
    """
    # Store token in user's home directory
    token_path = Path.home() / ".gmail_mcp_token.json"

    creds = None
    credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH')

    # Check for existing token
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Credentials file not found at {credentials_path}. "
                    "Please set GMAIL_CREDENTIALS_PATH environment variable to point to your credentials.json file."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

            # Save the token in the same directory as this file
            token_path.write_text(creds.to_json())

    try:
        # Return Gmail API service
        return build("gmail", "v1", credentials=creds)
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise error


# Example usage (only if run directly):
if __name__ == "__main__":
    try:
        service = get_gmail_service()
        print("Gmail API service created successfully!")
    except Exception as e:
        print(f"Failed to create Gmail service: {e}")

# Email Indexer and Timeline Generation Tool

This repository provides a comprehensive set of Python scripts to index, process, and retrieve emails from your inbox and to generate a chronological timeline based on email threads. The tools are designed to help you manage your email data, extract relevant information, and craft meaningful timelines that capture key events and milestones.

## Overview

The repository is organized into several modules:

- **Email Ingestion and Processing**:  
  Scripts in the `src/` directory (e.g., `email_fetcher.py`, `ingest.py`, and `thread_processor.py`) connect to your email account via the Gmail API, fetch email threads, and process them. The pipelines also support uploading processed data to external services such as Cloudflare and indexing with Pinecone.

- **Timeline Generation**:  
  The timeline crafting functionality is implemented in `src/timeline_tool.py` and `src/timeline_reconstruction.py`. These scripts leverage AI to generate human-readable timeline entries based on your email data.

## Usage Instructions

### Prerequisites

- **Python 3.11** or later.
- Install dependencies by running:
  ```bash
  pip install -r requirements.txt
  ```
- Configure environment variables:
  - Set `GMAIL_CREDENTIALS_PATH` to the path of your Gmail credentials file.
  - Set up API keys and other credentials in your `.env` file (e.g., for Cloudflare, Pinecone, and OpenRouter).

### Running the Email Ingestion Pipeline

To upload and index emails from your inbox, run the following command:

```bash
python3 src/ingest.py
```

This script will connect to your Gmail account, fetch the emails, process them (including attachments), and upload the processed data.

For a test run (e.g., processing emails from the last 7 days), use:

```bash
python3 src/ingest.py --test
```

### Using the Timeline Generation Tool

To generate a timeline based on your emails:

1. Run the timeline tool:
   ```bash
   python3 src/timeline_tool.py
   ```
2. When prompted, enter your query. For example:
   ```
   Show me the timeline for the enzyme patent
   ```
   The tool will:
   - Retrieve relevant emails from your inbox and test files.
   - Process and screen documents using AI-driven relevance checks.
   - Consolidate timeline entries in chronological order.
3. The generated timeline is saved to `data/timeline.txt`. To view the timeline, run:
   ```bash
   open data/timeline.txt
   ```

## Project Structure

- **src/**  
  Contains the main Python scripts:

  - `email_fetcher.py`: Handles fetching emails using the Gmail API.
  - `ingest.py`: Executes the email ingestion and processing pipeline.
  - `thread_processor.py`: Processes individual email threads.
  - `timeline_tool.py`: Provides a command-line interface for timeline queries.
  - `timeline_reconstruction.py`: Implements the timeline generation logic.

- **utils/**  
  Contains utility modules for API calls, file conversions, external integrations, etc.

- **data/**
  - Stores raw and processed email data.
  - Holds the generated timeline file (`timeline.txt`).

## Contributing

Contributions are welcome! Please ensure any new features or fixes come with appropriate tests and documentation updates.

## License

[Include your license information here.]

Happy indexing and timeline crafting!

import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv
from utils.prompts import information_extraction_prompt

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Add these constants at the top with your other imports
API_URL = "https://openrouter.ai/api/v1/chat/completions"


async def make_api_call(prompt, model="openai/o3-mini", session=None, max_retries=5, base_delay=1):
    """Make API call with exponential backoff retry logic."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
        "max_tokens": 100000
    }

    should_close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        should_close_session = True

    try:
        for attempt in range(max_retries):
            try:
                async with session.post(API_URL, json=data, headers=headers) as response:
                    if response.status == 200:
                        resp_json = await response.json()
                        if 'choices' in resp_json:
                            return resp_json['choices'][0]['message']['content']
                    elif response.status == 429:  # Rate limit exceeded
                        delay = base_delay * (2 ** attempt)
                        print(
                            f"Rate limit exceeded. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_text = await response.text()
                        print(
                            f"Error response (status {response.status}): {error_text}")

                    delay = base_delay * (2 ** attempt)
                    print(
                        f"Attempt {attempt+1} failed. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"All retry attempts failed. Final error: {str(e)}")
                    raise
                delay = base_delay * (2 ** attempt)
                print(
                    f"Error occurred: {str(e)}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    finally:
        if should_close_session:
            await session.close()

    raise Exception("Max retries exceeded")


async def test_concurrent_calls():
    # Create three different messages
    messages = [
        "What is the meaning of life?",
        "Tell me a joke",
        "What's the weather like?"
    ]

    # Create tasks for concurrent execution
    tasks = [make_api_call(msg) for msg in messages]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)

    # Print results
    for i, result in enumerate(results):
        print(f"\nResponse {i + 1} Content:")
        print(result)


def make_image_api_call(image_base64: str, prompt: str, model: str = "anthropic/claude-3.5-sonnet"):
    """Make an API call with both text and image content."""
    return {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        "json": {
            "model": model,
            "max_tokens": 100000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
        }
    }


async def extract_information(query: str, document: str, session=None):
    """
    Make an async call to retrieve relevant information using the
    'information_extraction_prompt'. The final result is returned directly.
    """
    formatted_prompt = information_extraction_prompt.format(
        query=query, document=document)
    result = await make_api_call(formatted_prompt, model="openai/o3-mini", session=session)
    return result


if __name__ == "__main__":
    asyncio.run(test_concurrent_calls())

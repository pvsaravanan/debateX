import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv

# Allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm import query_model
from backend.config import GROQ_API_KEY, GROQ_API_URL

async def test_direct_api(model: str):
    print(f"\n--- Testing Model '{model}' Direct API Call ---")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'hello' in exactly one word."}],
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result['choices'][0]['message']['content'].strip()}")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

async def test_backend_facade(model_with_prefix: str):
    print(f"\n--- Testing Model '{model_with_prefix}' Backend Router ---")
    try:
        result = await query_model(model_with_prefix, [{"role": "user", "content": "Say 'hello' in exactly one word."}])
        if result and 'content' in result:
            print(f"Facade Success!")
            print(f"Response: {result['content'].strip()}")
            if result.get('reasoning_details'):
                print(f"Reasoning Details: {result['reasoning_details']}")
        else:
            print(f"Facade returned invalid/empty response: {result}")
    except Exception as e:
        print(f"Facade Exception: {e}")

async def main():
    load_dotenv()
    print("Initializing Groq Connectivity Test...")
    print(f"API Key present: {'Yes' if GROQ_API_KEY else 'No'}")
    if GROQ_API_KEY:
        print(f"API Key hint: {GROQ_API_KEY[:8]}...")
    else:
        print("Warning: GROQ_API_KEY is not set in environment or .env file.")

    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]

    for model in models:
        # Test direct call
        await test_direct_api(model)
        # Test routing facade (which strips prefix)
        await test_backend_facade(f"groq/{model}")

if __name__ == "__main__":
    asyncio.run(main())

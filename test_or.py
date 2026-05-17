import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def test_model(model):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            print(f"Model: {model} - Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()['choices'][0]['message']['content']}")
            else:
                print(f"Error: {response.text}")
    except Exception as e:
        print(f"Model: {model} - Exception: {e}")

async def main():
    models = [
        "inclusionai/ring-2.6-1t:free",
        "deepseek/deepseek-v4-flash:free",
        "google/gemma-4-26b-a4b-it:free",
        "z-ai/glm-4.5-air:free",
        "google/gemini-2.5-flash"
    ]
    print(f"Testing with API Key: {OPENROUTER_API_KEY[:10]}...")
    for m in models:
        await test_model(m)

if __name__ == "__main__":
    asyncio.run(main())

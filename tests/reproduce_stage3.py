import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

async def main():
    model = "deepseek/deepseek-v4-flash:free"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "You are the moderator. Synthesize the debate: 'Hey! Debate about claude's model replacing human jobs.'"}],
    }
    print(f"Testing Stage 3 with model: {model}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()['choices'][0]['message']['content'][:200]}...")
            else:
                print(f"Error Text: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())

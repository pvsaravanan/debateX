import asyncio
import httpx
import os
import time
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
        "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
    }
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            latency = time.time() - start
            if response.status_code == 200:
                print(f"Model: {model} - SUCCESS in {latency:.2f}s - {response.json()['choices'][0]['message']['content'].strip()}")
            else:
                print(f"Model: {model} - FAILED in {latency:.2f}s - Status {response.status_code}")
    except Exception as e:
        latency = time.time() - start
        print(f"Model: {model} - EXCEPTION in {latency:.2f}s - {e}")

async def main():
    models = [
        "deepseek/deepseek-v4-flash:free",
        "z-ai/glm-4.5-air:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "nvidia/nemotron-3-nano-30b-a3b:free"
    ]
    tasks = [test_model(m) for m in models]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

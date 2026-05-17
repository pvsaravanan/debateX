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
        "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                print(f"Model: {model} - SUCCESS: {response.json()['choices'][0]['message']['content'].strip()}")
                return True
            else:
                print(f"Model: {model} - FAILED Status: {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        print(f"Model: {model} - EXCEPTION: {e}")
        return False

async def main():
    candidate_models = [
        "deepseek/deepseek-v4-flash:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "qwen/qwen3-coder:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "google/gemma-4-31b-it:free",
        "z-ai/glm-4.5-air:free",
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "liquid/lfm-2.5-1.2b-instruct:free"
    ]
    print(f"Testing free candidate models...")
    for m in candidate_models:
        await test_model(m)

if __name__ == "__main__":
    asyncio.run(main())

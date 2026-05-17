import httpx

async def main():
    url = "https://openrouter.ai/api/v1/models"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            models = response.json().get('data', [])
            free_models = []
            for m in models:
                id_ = m.get('id', '')
                pricing = m.get('pricing', {})
                prompt = float(pricing.get('prompt', 0))
                completion = float(pricing.get('completion', 0))
                # Check if id ends with :free or cost is 0
                if id_.endswith(':free') or (prompt == 0.0 and completion == 0.0):
                    free_models.append(id_)
            print("Found free models:")
            for fm in sorted(free_models):
                print(fm)
        else:
            print(f"Error fetching models: {response.status_code}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

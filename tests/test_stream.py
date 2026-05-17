import httpx
import json

async def main():
    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Create conversation
        res = await client.post("http://localhost:8001/api/conversations", json={})
        if res.status_code != 200:
            print("Failed to create conversation:", res.status_code, res.text)
            return
        conv = res.json()
        conv_id = conv['id']
        print(f"Created conversation: {conv_id}")

        # 2. Send message and stream
        print("Sending message and streaming debate...")
        payload = {"content": "Is water wet?"}
        
        async with client.stream("POST", f"http://localhost:8001/api/conversations/{conv_id}/message/stream", json=payload) as response:
            if response.status_code != 200:
                print("Failed to stream:", response.status_code)
                return
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        event = json.loads(data_str)
                        print(f"Event: {event.get('type')}")
                        if event.get('type') == 'stage1_complete':
                            print("  Stage 1 completed with responses count:", len(event.get('data', [])))
                        elif event.get('type') == 'stage2_complete':
                            print("  Stage 2 completed with rankings count:", len(event.get('data', [])))
                            print("  Aggregate rankings:", event.get('metadata', {}).get('aggregate_rankings'))
                        elif event.get('type') == 'stage3_complete':
                            print("  Stage 3 completed with synthesis size:", len(event.get('data', {}).get('response', '')))
                        elif event.get('type') == 'title_complete':
                            print("  Title generated:", event.get('data', {}).get('title'))
                        elif event.get('type') == 'error':
                            print("  ERROR:", event.get('message'))
                    except Exception as e:
                        print("  Failed to parse event:", e, "Line:", line)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

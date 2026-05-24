"""Groq API client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
from .config import GROQ_API_KEY, GROQ_API_URL

async def query_groq(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    temperature: float = 0.7,
) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                GROQ_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP Error {e.response.status_code}"
        try:
            err_json = e.response.json()
            if 'error' in err_json and 'message' in err_json['error']:
                error_msg = err_json['error']['message']
        except Exception:
            pass
        
        print(f"HTTP Error querying Groq model {model}: {e.response.status_code} - {error_msg}")
        raise ValueError(f"Groq API Error: {error_msg}")
    except Exception as e:
        import traceback
        err_msg = str(e) or type(e).__name__
        print(f"Error querying Groq model {model}: {err_msg}")
        traceback.print_exc()
        raise ValueError(f"Groq query failed: {err_msg}")

"""Facade for multiple LLM providers (OpenRouter, Groq)."""

from typing import List, Dict, Any, Optional
import asyncio
from .openrouter import query_openrouter
from .groq import query_groq

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    temperature: float = 0.7,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via the appropriate provider based on the prefix.
    """
    is_groq = model.startswith("groq/")

    if is_groq:
        actual_model = model[5:]  # Remove "groq/" prefix
        return await query_groq(actual_model, messages, timeout, temperature)
    else:
        # Default to OpenRouter
        return await query_openrouter(model, messages, timeout, temperature)

async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.
    """
    # Create tasks for all models
    tasks = [query_model(model, messages, temperature=temperature) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Check if any exception is a rate limit or credit error, and propagate it immediately
    for resp in responses:
        if isinstance(resp, Exception):
            err_str = str(resp)
            if "Rate limit" in err_str or "credits" in err_str or "429" in err_str or "402" in err_str:
                raise resp

    # Map models to their responses (converting other exceptions to None)
    mapped_responses = {}
    for model, resp in zip(models, responses):
        if isinstance(resp, Exception):
            print(f"Model {model} failed with exception: {resp}")
            mapped_responses[model] = None
        else:
            mapped_responses[model] = resp

    return mapped_responses

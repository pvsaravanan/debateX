"""Shared httpx.AsyncClient for connection pooling across API calls."""

import asyncio
import httpx

# Module-level shared client — reuses TCP/TLS connections across requests.
# Limits: max 20 concurrent connections, 10 keepalive connections.
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_client() -> httpx.AsyncClient:
    """
    Get or create the shared httpx.AsyncClient.

    The client is bound to the event loop it was created on; if the current
    loop differs (e.g. successive asyncio.run() calls in tests/scripts), a
    fresh client is created so pooled connections never outlive their loop.
    """
    global _client, _client_loop
    loop = asyncio.get_event_loop()
    if _client is None or _client.is_closed or _client_loop is not loop:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        _client_loop = loop
    return _client


async def close_client():
    """Close the shared client. Call during application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None

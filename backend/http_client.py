"""Shared httpx.AsyncClient for connection pooling across API calls."""

import httpx

# Module-level shared client — reuses TCP/TLS connections across requests.
# Limits: max 20 concurrent connections, 10 keepalive connections.
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx.AsyncClient."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    return _client


async def close_client():
    """Close the shared client. Call during application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None

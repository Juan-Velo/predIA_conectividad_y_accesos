"""Cliente HTTP compartido."""
import httpx

from app.config import USER_AGENT

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es"},
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


class ExternalServiceError(Exception):
    """Un servicio externo (Overpass, OSRM, Nominatim) no respondió correctamente."""

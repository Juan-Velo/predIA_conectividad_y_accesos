"""Geocodificación con Nominatim (máx. 1 solicitud por segundo según su política)."""
import asyncio
import time

import httpx

from app import config
from app.services import cache
from app.services.http import ExternalServiceError, client

_lock = asyncio.Lock()
_last_call = 0.0

# Caja aproximada de Lima Metropolitana y Callao para priorizar resultados
LIMA_VIEWBOX = "-77.25,-11.70,-76.70,-12.45"


async def _get(path: str, params: dict) -> object:
    global _last_call
    key = cache.make_key("nominatim", path, params)
    cached = cache.get(key)
    if cached is not None:
        return cached
    async with _lock:
        espera = 1.05 - (time.monotonic() - _last_call)
        if espera > 0:
            await asyncio.sleep(espera)
        try:
            resp = await client().get(f"{config.NOMINATIM_URL}/{path}", params=params)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Nominatim no respondió ({type(exc).__name__})") from exc
        finally:
            _last_call = time.monotonic()
    if resp.status_code != 200:
        raise ExternalServiceError(f"Nominatim respondió HTTP {resp.status_code}")
    data = resp.json()
    cache.set(key, data, config.CACHE_TTL_NOMINATIM_S)
    return data


def formatear_direccion(item: dict) -> dict:
    """Arma una dirección corta estilo 'Av. X 123, Distrito, Lima'."""
    a = item.get("address", {})
    via = a.get("road") or a.get("pedestrian") or a.get("footway") or a.get("square")
    lugar = a.get("neighbourhood") or a.get("suburb") or a.get("quarter")
    distrito = a.get("city_district") or a.get("city") or a.get("town") or a.get("village")
    linea1 = via or lugar or item.get("name") or ""
    if via and a.get("house_number"):
        linea1 = f"{via} {a['house_number']}"
    partes = [p for p in (linea1, distrito, a.get("region") or a.get("state")) if p]
    # Quita repeticiones (p. ej. "Lima, Lima")
    vistos, unicas = set(), []
    for p in partes:
        if p.lower() not in vistos:
            vistos.add(p.lower())
            unicas.append(p)
    return {
        "direccion": ", ".join(unicas) or item.get("display_name", ""),
        "distrito": distrito,
        "completa": item.get("display_name", ""),
    }


async def reverse(lat: float, lon: float) -> dict:
    data = await _get(
        "reverse",
        {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "format": "jsonv2", "zoom": 18, "addressdetails": 1},
    )
    if not isinstance(data, dict) or "error" in data:
        return {"direccion": f"{lat:.5f}, {lon:.5f}", "distrito": None, "completa": ""}
    return formatear_direccion(data)


async def search(q: str, limit: int = 6) -> list[dict]:
    data = await _get(
        "search",
        {
            "q": q,
            "format": "jsonv2",
            "addressdetails": 1,
            "countrycodes": "pe",
            "viewbox": LIMA_VIEWBOX,
            "limit": limit,
        },
    )
    resultados = []
    for item in data if isinstance(data, list) else []:
        f = formatear_direccion(item)
        resultados.append(
            {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "titulo": f["direccion"],
                "detalle": item.get("display_name", ""),
                "tipo": item.get("type"),
            }
        )
    return resultados

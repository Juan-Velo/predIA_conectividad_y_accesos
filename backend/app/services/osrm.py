"""Tiempos y distancias por red vial real usando OSRM (servicio table)."""
import logging

import httpx

from app import config
from app.services import cache
from app.services.http import ExternalServiceError, client

log = logging.getLogger(__name__)


async def tabla_desde(
    origen: tuple[float, float], destinos: list[tuple[float, float]], perfil: str
) -> list[dict | None]:
    """Distancia (m) y duración (s) desde `origen` a cada destino. Coordenadas en (lat, lon).

    Devuelve una lista alineada con `destinos`; None si no hay ruta.
    """
    if not destinos:
        return []
    puntos = [origen, *destinos]
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in puntos)
    key = cache.make_key("osrm", perfil, coords)
    cached = cache.get(key)
    if cached is not None:
        return cached

    errors = []
    for base in config.OSRM_PROFILES[perfil]:
        url = f"{base}/{coords}"
        try:
            resp = await client().get(
                url,
                params={"sources": "0", "annotations": "duration,distance"},
                timeout=httpx.Timeout(8.0, connect=5.0),
            )
            data = resp.json()
            if resp.status_code != 200 or data.get("code") != "Ok":
                errors.append(f"{base}: {data.get('code', resp.status_code)}")
                continue
            durs = data["durations"][0][1:]
            dists = data["distances"][0][1:]
            result = [
                None if d is None or s is None else {"distancia_m": round(d), "duracion_s": round(s)}
                for d, s in zip(dists, durs)
            ]
            cache.set(key, result, config.CACHE_TTL_OSRM_S)
            return result
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            errors.append(f"{base}: {type(exc).__name__}")
    log.warning("OSRM %s falló: %s", perfil, errors)
    raise ExternalServiceError(f"No se pudo calcular rutas ({perfil}). " + "; ".join(errors))

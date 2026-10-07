"""Consultas a Overpass API (datos de OpenStreetMap)."""
import asyncio
import logging

import httpx

from app import config
from app.services import cache
from app.services.http import ExternalServiceError, client

log = logging.getLogger(__name__)

# Una consulta a la vez: evita agotar los "slots" por IP del servidor público
_sem = asyncio.Semaphore(1)

VIAS_EXPRESAS = "motorway|trunk|motorway_link|trunk_link"
VIAS_URBANAS = (
    "primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|"
    "residential|unclassified|living_street"
)


async def run_query(query: str) -> dict:
    """Ejecuta una consulta Overpass QL con caché y servidores de respaldo."""
    key = cache.make_key("overpass", query)
    cached = cache.get(key)
    if cached is not None:
        return cached
    async with _sem:
        return await _run_uncached(key, query)


async def _run_uncached(key: str, query: str) -> dict:
    # Otra solicitud pudo haberla resuelto mientras se esperaba el turno
    cached = cache.get(key)
    if cached is not None:
        return cached
    errors = []
    # El servidor principal limita a pocas consultas simultáneas por IP (HTTP 429):
    # se reintenta con espera antes de pasar a los espejos, que suelen ser más lentos.
    intentos = [config.OVERPASS_ENDPOINTS[0]] * 3 + config.OVERPASS_ENDPOINTS[1:]
    for i, endpoint in enumerate(intentos):
        try:
            resp = await client().post(
                endpoint,
                data={"data": query},
                timeout=httpx.Timeout(config.OVERPASS_TIMEOUT_S, connect=10.0),
            )
            if resp.status_code in (429, 504) and i < 2:
                errors.append(f"{endpoint}: HTTP {resp.status_code}")
                await asyncio.sleep(4 * (i + 1))
                continue
            if resp.status_code != 200:
                errors.append(f"{endpoint}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            if "remark" in data and "error" in data["remark"].lower():
                errors.append(f"{endpoint}: {data['remark'][:120]}")
                continue
            cache.set(key, data, config.CACHE_TTL_OVERPASS_S)
            return data
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"{endpoint}: {type(exc).__name__}")
    log.warning("Overpass falló en todos los servidores: %s", errors)
    raise ExternalServiceError("No se pudo consultar OpenStreetMap (Overpass). " + "; ".join(errors))


def _r(v: float) -> float:
    # Redondeo a ~1 m para que clics casi idénticos compartan caché
    return round(v, 5)


def _celda(lat: float, lon: float, paso: float) -> tuple[float, float]:
    """Centro de la celda de grilla que contiene el punto (para reutilizar caché entre clics)."""
    return (round(round(lat / paso) * paso, 5), round(round(lon / paso) * paso, 5))


# Tamaño de celda en grados y margen que garantiza cubrir el radio desde cualquier punto de la celda
_PASO_ZONA, _MARGEN_ZONA = 0.005, 400  # ~550 m
_PASO_EXPRESAS, _MARGEN_EXPRESAS = 0.02, 1600  # ~2.2 km


async def red_vial_y_transporte(lat: float, lon: float) -> dict:
    """Vías clasificables, paraderos y estaciones alrededor del punto.

    Se hacen dos consultas cacheadas por celda: la red urbana cercana y las vías
    expresas (radio mayor). El filtrado fino por distancia se hace en Python.
    """
    c = config
    zlat, zlon = _celda(lat, lon, _PASO_ZONA)
    m = _MARGEN_ZONA
    zona = f"""
[out:json][timeout:{c.OVERPASS_TIMEOUT_S - 10}];
(
  way(around:{c.RADIO_VIAS_M + m},{zlat},{zlon})[highway~"^({VIAS_URBANAS})$"];
  way(around:{200 + m},{zlat},{zlon})[highway~"^(service|track|pedestrian|footway|path|steps)$"];
)->.vias;
.vias out tags geom;
(
  node(around:{c.RADIO_PARADEROS_M + m},{zlat},{zlon})[highway=bus_stop];
  node(around:{c.RADIO_PARADEROS_M + m},{zlat},{zlon})[public_transport=platform];
  nwr(around:{c.RADIO_ESTACIONES_M + m},{zlat},{zlon})[railway~"^(station|halt)$"];
  nwr(around:{c.RADIO_ESTACIONES_M + m},{zlat},{zlon})[public_transport=station];
)->.tp;
.tp out tags center;
"""
    elat, elon = _celda(lat, lon, _PASO_EXPRESAS)
    expresas = f"""
[out:json][timeout:{c.OVERPASS_TIMEOUT_S - 10}];
way(around:{c.RADIO_EXPRESAS_M + _MARGEN_EXPRESAS},{elat},{elon})[highway~"^({VIAS_EXPRESAS})$"];
out tags geom;
"""
    a = await run_query(zona)
    b = await run_query(expresas)
    return {"elements": a.get("elements", []) + b.get("elements", [])}


async def entorno_terreno(lat: float, lon: float) -> dict:
    """Polígonos candidatos a terreno (canchas, áreas verdes, baldíos) alrededor del punto."""
    lat, lon = _celda(lat, lon, 0.002)  # ~220 m; el margen de 160 m cubre toda la celda
    r = config.RADIO_TERRENOS_M + 160
    query = f"""
[out:json][timeout:40];
(
  way(around:{r},{lat},{lon})[leisure~"^(pitch|park|sports_centre|playground|stadium|recreation_ground|garden)$"];
  way(around:{r},{lat},{lon})[landuse~"^(grass|brownfield|greenfield|construction|meadow|vacant|recreation_ground|village_green|farmland)$"];
  way(around:{r},{lat},{lon})[natural~"^(scrub|grassland|sand|bare_rock|heath)$"];
);
out tags geom;
"""
    return await run_query(query)


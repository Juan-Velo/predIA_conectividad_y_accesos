"""Endpoints REST de la pantalla Conectividad y accesos."""
import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app import config
from app.core.conectividad import analizar_conectividad
from app.core.terreno import analizar_terreno
from app.services import nominatim
from app.services.http import ExternalServiceError

router = APIRouter(prefix="/api")

Lat = Query(config.DEFAULT_LAT, ge=-90, le=90)
Lon = Query(config.DEFAULT_LON, ge=-180, le=180)


class AnalisisRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    poligono: list[tuple[float, float]] | None = Field(
        default=None, description="Vértices [lat, lon] dibujados por el usuario", min_length=3
    )


def _error(exc: ExternalServiceError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/health")
async def health():
    return {"status": "ok", "default": {"lat": config.DEFAULT_LAT, "lon": config.DEFAULT_LON}}


@router.get("/geocode/search")
async def geocode_search(q: str = Query(min_length=3, max_length=200)):
    try:
        return await nominatim.search(q)
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.get("/terreno")
async def terreno(lat: float = Lat, lon: float = Lon):
    try:
        return await analizar_terreno(lat, lon)
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.post("/terreno")
async def terreno_poligono(req: AnalisisRequest):
    try:
        return await analizar_terreno(req.lat, req.lon, req.poligono)
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.get("/conectividad")
async def conectividad(lat: float = Lat, lon: float = Lon):
    """Analiza el terreno detectado en el punto (o el punto mismo si no hay polígono)."""
    try:
        t = await analizar_terreno(lat, lon)
        return await analizar_conectividad(t["lat"], t["lon"], t["poligono"])
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.post("/conectividad")
async def conectividad_poligono(req: AnalisisRequest):
    try:
        return await analizar_conectividad(req.lat, req.lon, req.poligono)
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.get("/analisis")
async def analisis(lat: float = Lat, lon: float = Lon):
    """Terreno + conectividad en una sola llamada (lo que usa el frontend)."""
    try:
        t = await analizar_terreno(lat, lon)
        c = await analizar_conectividad(t["lat"], t["lon"], t["poligono"])
        return {"terreno": t, "conectividad": c}
    except ExternalServiceError as exc:
        raise _error(exc) from exc


@router.post("/analisis")
async def analisis_poligono(req: AnalisisRequest):
    try:
        t, c = await asyncio.gather(
            analizar_terreno(req.lat, req.lon, req.poligono),
            analizar_conectividad(req.lat, req.lon, req.poligono),
        )
        return {"terreno": t, "conectividad": c}
    except ExternalServiceError as exc:
        raise _error(exc) from exc

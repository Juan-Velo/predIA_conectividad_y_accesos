"""PredIA — backend beta de la pantalla 'Conectividad y accesos'.

Ejecutar:  uvicorn app.main:app --reload --port 8000
Docs:      http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import router
from app.services import http

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await http.close()


app = FastAPI(
    title="PredIA API (beta)",
    description="Conectividad y accesos de terrenos usando datos abiertos (OSM, OSRM, Esri).",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

# Si existe el build del frontend, FastAPI también lo sirve (un solo proceso en producción)
_dist = config.BASE_DIR.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")

"""Configuración central del backend de PredIA (beta)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Punto de estudio por defecto (coordenadas del centro de la zona, Chorrillos)
# 12°10'46.26"S 76°59'56.88"W
DEFAULT_LAT = -12.179517
DEFAULT_LON = -76.999133

# Identificación ante servicios públicos de OSM (requisito de sus políticas de uso)
USER_AGENT = "PredIA-beta/0.1 (proyecto academico UTEC)"

# Overpass: se prueban en orden; si uno falla o limita, se usa el siguiente
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_TIMEOUT_S = 90

NOMINATIM_URL = "https://nominatim.openstreetmap.org"

# OSRM: demo pública (auto) y FOSSGIS (auto de respaldo y peatón)
OSRM_PROFILES = {
    "driving": [
        "https://router.project-osrm.org/table/v1/driving",
        "https://routing.openstreetmap.de/routed-car/table/v1/driving",
    ],
    "foot": [
        "https://routing.openstreetmap.de/routed-foot/table/v1/foot",
    ],
}

# Radios de análisis (metros)
RADIO_VIAS_M = 1500  # arteriales, colectoras y locales dibujadas en el mapa
RADIO_EXPRESAS_M = 5000  # vías expresas suelen estar más lejos
RADIO_PARADEROS_M = 1500
RADIO_ESTACIONES_M = 4000
RADIO_TERRENOS_M = 400

# A partir de esta distancia en línea recta, el tiempo se muestra en vehículo
UMBRAL_CAMINANDO_M = 1000

# Caché
CACHE_PATH = BASE_DIR / "cache.sqlite3"
CACHE_TTL_OVERPASS_S = 24 * 3600
CACHE_TTL_OSRM_S = 7 * 24 * 3600
CACHE_TTL_NOMINATIM_S = 7 * 24 * 3600

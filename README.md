# PredIA · Conectividad y accesos (beta)

Pantalla **Ubicación y entorno → Conectividad** de PredIA: analiza la red vial, el
transporte público y los tiempos de acceso de un terreno en Lima con datos reales.

- **Backend:** FastAPI (Python 3.11+), en `backend/`
- **Frontend:** React + Vite + Leaflet, en `frontend/`
- **APIs externas (gratis, sin API key):**

| Para qué | Servicio |
|---|---|
| Calles, jerarquía vial, paraderos, estaciones, canchas/áreas verdes | OpenStreetMap vía **Overpass API** |
| Tiempos y distancias por red vial (auto / a pie) | **OSRM** (router.project-osrm.org y routing.openstreetmap.de) |
| Dirección del terreno y buscador | **Nominatim** (OSM) |
| Imagen satelital y miniatura | **Esri World Imagery** |
| Mapa base | **CARTO Voyager** |

## Cómo correrlo

Requisitos: Python 3.11+ y Node 20+.

```bash
# 1) Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
# 2) Frontend (otra terminal)
cd frontend
npm install
npm run dev                        # http://localhost:5173  (redirige /api al backend)
```

Documentación interactiva de la API: http://localhost:8000/docs

**Modo un solo servidor:** `cd frontend && npm run build`. Luego basta con el
backend: FastAPI sirve el build en http://localhost:8000.

## Cómo se usa

- Al abrir se analiza el punto de estudio (Chorrillos, 12°10'46.26"S 76°59'56.88"W).
- **Clic en el mapa:** analiza ese punto. Si cae en una cancha o área verde mapeada en OSM,
  se toma su polígono y su área.
- **Contornos punteados blancos:** terrenos candidatos cercanos (canchas, parques,
  áreas verdes, baldíos). Clic para analizarlos.
- **Dibujar terreno:** marca los vértices y luego ✓ para analizar un polígono propio.
- **Buscador:** escribe una dirección y presiona Enter. Nominatim no permite autocompletar.
- **Red vial cercana:** clic en una vía para resaltarla y ver el punto de acceso.
- **Filtros:** encienden o apagan cada tipo de vía y el transporte (paraderos o estaciones).

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/analisis?lat=&lon=` | Terreno + conectividad (lo que usa el frontend) |
| POST | `/api/analisis` | Igual, con `{lat, lon, poligono: [[lat,lon],...]}` |
| GET/POST | `/api/terreno` | Dirección, polígono, área, uso actual, miniatura, candidatos |
| GET/POST | `/api/conectividad` | Vías por tipo (GeoJSON), red vial cercana, observaciones, acceso, transporte |
| GET | `/api/geocode/search?q=` | Búsqueda de direcciones en Lima |
| GET | `/api/health` | Estado |

## Cómo se calcula

- **Clasificación vial** (etiqueta `highway` de OSM):
  - motorway / trunk → **expresa**
  - primary → **arterial**
  - secondary / tertiary → **colectora**
  - residential / unclassified / living_street → **local**
- **Red vial cercana:** la vía más cercana de cada tipo, con distancia y tiempo **por ruta
  real** (OSRM). Hasta 1 km en línea recta se muestra a pie; más lejos, en vehículo. La vía
  local a menos de 30 m cuenta como "frente al terreno".
- **Acceso al terreno:**
  - Tipo de vía frontal: la vía más cercana al polígono.
  - Ancho: `width` de OSM si existe; si no, carriles × 3.3 m + veredas; si no, un valor
    típico por tipo de vía (por eso se muestra "≈").
- **Observaciones:** reglas simples sobre esos datos:
  - Arterial a menos de 500 m.
  - Vía expresa a 10 min o menos.
  - Paradero a menos de 400 m.
  - Estación del Metro o del Metropolitano a menos de 2.5 km.
  - Tráfico y ruido estimados por cercanía a vías expresas o arteriales.

## Limitaciones de la beta

- Los **tiempos son sin tráfico** (OSRM). No hay una API de tráfico en tiempo real gratis y
  sin key, así que "tráfico elevado" es una **estimación** por cercanía a vías principales.
- La calidad depende de OpenStreetMap. En Lima la jerarquía vial está bien mapeada, pero el
  ancho de vía casi nunca está registrado y muchos terrenos no tienen polígono (de ahí la
  opción de dibujarlo).
- Overpass es un servicio público con límite por IP:
  - El **primer análisis de una zona tarda ~30–45 s**.
  - Luego queda en caché 24 h (`backend/cache.sqlite3`) y los clics cercanos tardan ~1–10 s.
  - Si el servidor principal falla, se reintenta y luego se prueban espejos.
- El menú lateral y las pestañas superiores (Resumen, Análisis, etc.) están deshabilitados
  porque corresponden a otras pantallas.

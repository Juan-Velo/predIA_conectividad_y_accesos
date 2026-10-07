"""Detección del terreno (polígono, área y uso actual) alrededor de un punto."""
import asyncio
import math

from shapely.geometry import Polygon

from app.config import RADIO_TERRENOS_M
from app.core.geo import ProyeccionLocal
from app.services import nominatim, overpass

# Distancia máxima para asociar el clic a un polígono que no lo contiene
DIST_MAX_CANDIDATO_M = 50
# Área mínima para listar un polígono como terreno candidato (m²)
AREA_MIN_CANDIDATO_M2 = 400

_USOS = {
    ("leisure", "pitch"): "Cancha deportiva",
    ("leisure", "park"): "Parque",
    ("leisure", "sports_centre"): "Complejo deportivo",
    ("leisure", "playground"): "Zona de juegos",
    ("leisure", "stadium"): "Estadio",
    ("leisure", "recreation_ground"): "Área recreativa",
    ("leisure", "garden"): "Jardín",
    ("landuse", "grass"): "Área verde",
    ("landuse", "brownfield"): "Terreno baldío",
    ("landuse", "greenfield"): "Sin edificar",
    ("landuse", "construction"): "En construcción",
    ("landuse", "meadow"): "Área verde",
    ("landuse", "vacant"): "Sin edificar",
    ("landuse", "recreation_ground"): "Área recreativa",
    ("landuse", "village_green"): "Área verde",
    ("landuse", "farmland"): "Agrícola",
    ("natural", "scrub"): "Sin edificar (matorral)",
    ("natural", "grassland"): "Sin edificar (pastizal)",
    ("natural", "sand"): "Sin edificar (arenal)",
    ("natural", "bare_rock"): "Sin edificar (roca)",
    ("natural", "heath"): "Sin edificar",
}

_DEPORTES = {
    "soccer": "fútbol",
    "basketball": "básquet",
    "volleyball": "vóley",
    "tennis": "tenis",
    "multi": "multideporte",
}


def uso_desde_tags(tags: dict) -> str:
    if "building" in tags:
        return "Edificado"
    for clave in ("leisure", "landuse", "natural"):
        if clave in tags:
            uso = _USOS.get((clave, tags[clave]), tags[clave])
            if tags.get(clave) == "pitch" and tags.get("sport") in _DEPORTES:
                uso = f"Cancha de {_DEPORTES[tags['sport']]}"
            return uso
    return "Sin datos"


def _candidatos(data: dict, proj: ProyeccionLocal) -> list[dict]:
    res = []
    for el in data.get("elements", []):
        geom = el.get("geometry")
        if el.get("type") != "way" or not geom or len(geom) < 4:
            continue
        if geom[0] != geom[-1]:  # solo vías cerradas (polígonos)
            continue
        latlons = [(g["lat"], g["lon"]) for g in geom]
        poly = proj.poligono(latlons)
        if poly is None:
            continue
        res.append({"tags": el.get("tags", {}), "latlons": latlons, "poly": poly, "id": el["id"]})
    return res


ESRI_TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"


def _pixel_global(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Coordenadas de píxel Web Mercator (teselas de 256 px) en el zoom z."""
    n = 256 * 2**z
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def miniatura(latlons: list[tuple[float, float]], max_px: float = 56) -> dict:
    """Bloque de 2x2 teselas satelitales centrado en el terreno + contorno en píxeles.

    El frontend las compone y recorta; así no dependemos del endpoint `export`
    de Esri, que es lento e intermitente.
    """
    lat_c = sum(p[0] for p in latlons) / len(latlons)
    lon_c = sum(p[1] for p in latlons) / len(latlons)
    z = 19
    while z > 14:
        pts = [_pixel_global(a, b, z) for a, b in latlons]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if max(max(xs) - min(xs), max(ys) - min(ys)) <= max_px:
            break
        z -= 1
    cx, cy = _pixel_global(lat_c, lon_c, z)
    # Bloque 2x2 cuyo centro queda más cerca del centroide
    x0 = round(cx / 256) - 1
    y0 = round(cy / 256) - 1
    teselas = [
        {"url": f"{ESRI_TILE}/{z}/{y0 + j}/{x0 + i}", "x": i * 256, "y": j * 256}
        for j in range(2)
        for i in range(2)
    ]
    contorno = (
        [[round(px - x0 * 256, 1), round(py - y0 * 256, 1)]
         for px, py in (_pixel_global(a, b, z) for a, b in latlons)]
        if len(latlons) >= 3
        else []
    )
    return {
        "zoom": z,
        "teselas": teselas,
        "centro_px": [round(cx - x0 * 256, 1), round(cy - y0 * 256, 1)],
        "contorno_px": contorno,
    }


def elegir_poligono(lat: float, lon: float, data: dict) -> dict | None:
    """Elige el polígono que mejor representa el terreno clicado."""
    proj = ProyeccionLocal(lat, lon)
    p = proj.punto(lat, lon)
    cands = _candidatos(data, proj)
    terrenos = [c for c in cands if "building" not in c["tags"]]

    # 1) El terreno libre más pequeño que contiene el punto (p. ej. una cancha dentro de un parque)
    contienen = [c for c in terrenos if c["poly"].contains(p)]
    if contienen:
        return min(contienen, key=lambda c: c["poly"].area)
    # 2) El terreno libre más cercano
    if terrenos:
        cerca = min(terrenos, key=lambda c: c["poly"].distance(p))
        if cerca["poly"].distance(p) <= DIST_MAX_CANDIDATO_M:
            return cerca
    return None


async def analizar_terreno(
    lat: float, lon: float, poligono_usuario: list[tuple[float, float]] | None = None
) -> dict:
    """Devuelve dirección, polígono (lista lat/lon), área, uso y miniatura del terreno."""
    if poligono_usuario:
        proj = ProyeccionLocal(lat, lon)
        poly: Polygon | None = proj.poligono(poligono_usuario)
        if poly is not None:
            c = poly.centroid
            lat, lon = proj.latlon(c.x, c.y)

    entorno, direccion = await asyncio.gather(
        overpass.entorno_terreno(lat, lon), nominatim.reverse(lat, lon)
    )

    proj = ProyeccionLocal(lat, lon)
    if poligono_usuario:
        latlons = poligono_usuario
        if latlons[0] != latlons[-1]:
            latlons = [*latlons, latlons[0]]
        poly = proj.poligono(latlons)
        detectado = elegir_poligono(lat, lon, entorno)
        uso = uso_desde_tags(detectado["tags"]) if detectado else "Sin datos"
        fuente = "usuario"
        nombre = None
    else:
        detectado = elegir_poligono(lat, lon, entorno)
        if detectado:
            latlons, poly = detectado["latlons"], detectado["poly"]
            uso = uso_desde_tags(detectado["tags"])
            nombre = detectado["tags"].get("name")
            fuente = "osm"
        else:
            latlons, poly, uso, nombre, fuente = None, None, "Sin datos", None, None

    candidatos = [
        {
            "osm_id": c["id"],
            "uso": uso_desde_tags(c["tags"]),
            "nombre": c["tags"].get("name"),
            "area_m2": round(c["poly"].area),
            "centro": [round(v, 7) for v in proj.latlon(c["poly"].centroid.x, c["poly"].centroid.y)],
            "poligono": [[round(a, 7), round(b, 7)] for a, b in c["latlons"]],
        }
        for c in _candidatos(entorno, proj)
        if "building" not in c["tags"]
        and c["poly"].area >= AREA_MIN_CANDIDATO_M2
        and c["poly"].distance(proj.punto(lat, lon)) <= RADIO_TERRENOS_M
    ]

    area = round(poly.area) if poly is not None else None
    perimetro = round(poly.length) if poly is not None else None
    imagen_latlons = latlons or [(lat, lon)]

    return {
        "lat": lat,
        "lon": lon,
        "direccion": direccion["direccion"],
        "direccion_completa": direccion["completa"],
        "distrito": direccion["distrito"],
        "nombre": nombre,
        "poligono": [[round(a, 7), round(b, 7)] for a, b in latlons] if latlons else None,
        "fuente_poligono": fuente,
        "area_m2": area,
        "perimetro_m": perimetro,
        "uso_actual": uso,
        "miniatura": miniatura(imagen_latlons),
        "candidatos": candidatos,
    }

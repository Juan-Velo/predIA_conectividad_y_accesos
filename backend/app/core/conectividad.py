"""Análisis de conectividad y accesos de un terreno."""
import asyncio
import logging
import math
from datetime import datetime, timezone

from shapely.geometry import Point

from app import config
from app.core import clasificacion as cl
from app.core.geo import ProyeccionLocal, punto_mas_cercano
from app.services import osrm, overpass

log = logging.getLogger(__name__)

# Si la vía local más cercana está a menos de esto, se considera frente al terreno
DIST_FRENTE_M = 30
# Velocidades de respaldo si OSRM no responde (m/s) y factor de desvío de la red
VEL_PIE = 1.3
VEL_AUTO = 25 / 3.6
FACTOR_DESVIO = 1.35


def _tipo_estacion(tags: dict) -> str | None:
    """'metro' (Línea 1/2), 'metropolitano' (BRT) o 'corredor'; None si no es de pasajeros
    relevante (tranvía histórico de Barranco, patios, terminales interprovinciales)."""
    if tags.get("station") in ("subway", "light_rail", "train") or any(
        tags.get(k) == "yes" for k in ("train", "subway", "light_rail")
    ):
        return "metro"
    texto = " ".join(tags.get(k, "") for k in ("network", "operator", "name")).lower()
    if "patio" in texto:
        return None
    if "metropolitano" in texto:
        return "metropolitano"
    if "corredor" in texto:
        return "corredor"
    return None


ETIQUETA_ESTACION = {"metro": "Metro", "metropolitano": "Metropolitano", "corredor": "Corredor"}


_RADIO_POR_CLASE = {
    "expresa": config.RADIO_EXPRESAS_M,
    "arterial": config.RADIO_VIAS_M,
    "colectora": config.RADIO_VIAS_M,
    "local": config.RADIO_VIAS_M,
    "servicio": 200,
    "peatonal": 200,
}


def _parsear(data: dict, proj: ProyeccionLocal):
    vias, paraderos, estaciones = [], [], []
    origen = Point(0, 0)
    vistos: set[int] = set()
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        if el["type"] == "way" and "geometry" in el and cl.clase_de(tags.get("highway", "")):
            if el["id"] in vistos:
                continue
            vistos.add(el["id"])
            linea = proj.linea(el["geometry"])
            if linea is None or linea.distance(origen) > _RADIO_POR_CLASE[cl.clase_de(tags["highway"])]:
                continue
            vias.append(
                {
                    "id": el["id"],
                    "tags": tags,
                    "highway": tags["highway"],
                    "clase": cl.clase_de(tags["highway"]),
                    "nombre": tags.get("name"),
                    "linea": linea,
                    "geometry": el["geometry"],
                }
            )
            continue

        if el["type"] == "node":
            plat, plon = el["lat"], el["lon"]
        elif "center" in el:
            plat, plon = el["center"]["lat"], el["center"]["lon"]
        else:
            continue
        dist = math.dist(proj.xy(plat, plon), (0, 0))
        es_estacion = tags.get("railway") in ("station", "halt") or tags.get("public_transport") == "station"
        if dist > (config.RADIO_ESTACIONES_M if es_estacion else config.RADIO_PARADEROS_M):
            continue
        item = {
            "nombre": tags.get("name"),
            "lat": plat,
            "lon": plon,
            "xy": proj.xy(plat, plon),
        }
        if es_estacion:
            tipo = _tipo_estacion(tags)
            if tipo is None:
                continue
            item["tipo"] = tipo
            item["red"] = tags.get("network") or ETIQUETA_ESTACION[tipo]
            estaciones.append(item)
        else:
            item["tipo"] = "paradero"
            paraderos.append(item)

    return vias, _deduplicar(paraderos, 20), _deduplicar(estaciones, 300)


def _deduplicar(items: list[dict], radio_m: float) -> list[dict]:
    """Une puntos que representan lo mismo (p. ej. nodo `bus_stop` y `platform`)."""
    unicos: list[dict] = []
    for it in items:
        dup = next(
            (
                u
                for u in unicos
                if math.dist(u["xy"], it["xy"]) <= radio_m
                and (radio_m <= 20 or (u["nombre"] or "") == (it["nombre"] or ""))
            ),
            None,
        )
        if dup is None:
            unicos.append(it)
        elif not dup["nombre"] and it["nombre"]:
            dup["nombre"] = it["nombre"]
    return unicos


def _mas_cercana(vias: list[dict], geom, clases: tuple[str, ...]) -> dict | None:
    """Vía más cercana de las clases dadas; prefiere vías con nombre."""
    mejor, mejor_score = None, float("inf")
    for v in vias:
        if v["clase"] not in clases or cl.es_enlace(v["highway"]):
            continue
        d = geom.distance(v["linea"])
        score = d + (0 if v["nombre"] else 80)
        if score < mejor_score:
            mejor, mejor_score = v, score
    return mejor


def _estimar(recta_m: float, modo: str) -> dict:
    dist = recta_m * FACTOR_DESVIO
    vel = VEL_PIE if modo == "foot" else VEL_AUTO
    return {"distancia_m": round(dist), "duracion_s": round(dist / vel), "estimado": True}


def _minutos(segundos: float) -> int:
    return max(1, math.ceil(segundos / 60))


def _texto_distancia(m: float) -> str:
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{round(m / 10) * 10:.0f} m"


async def analizar_conectividad(
    lat: float, lon: float, poligono: list[tuple[float, float]] | None = None
) -> dict:
    proj = ProyeccionLocal(lat, lon)
    geom_terreno = (proj.poligono(poligono) if poligono else None) or proj.punto(lat, lon)

    data = await overpass.red_vial_y_transporte(lat, lon)
    vias, paraderos, estaciones = _parsear(data, proj)

    # --- Vía más cercana por clase + vía frontal -------------------------------------------
    seleccion: list[tuple[str, dict]] = []
    for clase in cl.CLASES:
        v = _mas_cercana(vias, geom_terreno, (clase,))
        if v:
            seleccion.append((clase, v))
    frontal = _mas_cercana(vias, geom_terreno, (*cl.CLASES, "servicio", "peatonal"))
    frontal_vehicular = _mas_cercana(vias, geom_terreno, (*cl.CLASES, "servicio"))

    for p in paraderos:
        p["recta_m"] = geom_terreno.distance(proj.punto(p["lat"], p["lon"]))
    for e in estaciones:
        e["recta_m"] = geom_terreno.distance(proj.punto(e["lat"], e["lon"]))
    paraderos.sort(key=lambda p: p["recta_m"])
    estaciones.sort(key=lambda e: e["recta_m"])

    # --- Destinos para el ruteo --------------------------------------------------------------
    destinos: list[dict] = []
    for clase, v in seleccion:
        (x, y), recta = punto_mas_cercano(geom_terreno, v["linea"])
        destinos.append(
            {
                "clase": clase,
                "via": v,
                "latlon": proj.latlon(x, y),
                "recta_m": recta,
                "modo": "foot" if recta <= config.UMBRAL_CAMINANDO_M else "driving",
            }
        )
    if paraderos:
        p = paraderos[0]
        destinos.append({"clase": "paradero", "item": p, "latlon": (p["lat"], p["lon"]),
                         "recta_m": p["recta_m"], "modo": "foot"})
    if estaciones:
        e = estaciones[0]
        destinos.append({"clase": "estacion", "item": e, "latlon": (e["lat"], e["lon"]),
                         "recta_m": e["recta_m"],
                         "modo": "foot" if e["recta_m"] <= config.UMBRAL_CAMINANDO_M else "driving"})

    origen = (lat, lon)
    por_modo = {"foot": [d for d in destinos if d["modo"] == "foot"],
                "driving": [d for d in destinos if d["modo"] == "driving"]}
    resultados = await asyncio.gather(
        *(osrm.tabla_desde(origen, [d["latlon"] for d in lst], modo) for modo, lst in por_modo.items()),
        return_exceptions=True,
    )
    for (modo, lst), res in zip(por_modo.items(), resultados):
        if isinstance(res, Exception):
            log.warning("Ruteo %s no disponible, se estima: %s", modo, res)
            res = [None] * len(lst)
        for d, r in zip(lst, res):
            d["ruta"] = {**r, "estimado": False} if r else _estimar(d["recta_m"], modo)

    # --- Red vial cercana --------------------------------------------------------------------
    red_vial = []
    for d in destinos:
        if d["clase"] not in cl.CLASES:
            continue
        v, ruta = d["via"], d["ruta"]
        frente = d["clase"] == "local" and d["recta_m"] <= DIST_FRENTE_M
        nombre = v["nombre"] or "Vía sin nombre"
        red_vial.append(
            {
                "clase": d["clase"],
                "etiqueta": cl.ETIQUETAS[d["clase"]],
                "nombre": cl.abreviar_nombre(nombre),
                "nombre_completo": nombre,
                "osm_id": v["id"],
                "recta_m": round(d["recta_m"]),
                "distancia_m": ruta["distancia_m"],
                "duracion_min": _minutos(ruta["duracion_s"]),
                "modo": "caminando" if d["modo"] == "foot" else "vehiculo",
                "frente_al_terreno": frente,
                "estimado": ruta["estimado"],
                "punto_acceso": [round(c, 6) for c in d["latlon"]],
            }
        )

    # --- Transporte ---------------------------------------------------------------------------
    d_paradero = next((d for d in destinos if d["clase"] == "paradero"), None)
    d_estacion = next((d for d in destinos if d["clase"] == "estacion"), None)

    def _tp(it: dict) -> dict:
        return {"nombre": it["nombre"], "lat": it["lat"], "lon": it["lon"],
                "tipo": it["tipo"], "recta_m": round(it["recta_m"])}

    transporte = {
        "paraderos": [_tp(p) for p in paraderos],
        "estaciones": [{**_tp(e), "red": e.get("red")} for e in estaciones],
        "paradero_cercano": None,
        "estacion_cercana": None,
    }
    if d_paradero:
        transporte["paradero_cercano"] = {
            **_tp(d_paradero["item"]),
            "distancia_m": d_paradero["ruta"]["distancia_m"],
            "duracion_min": _minutos(d_paradero["ruta"]["duracion_s"]),
        }
    if d_estacion:
        transporte["estacion_cercana"] = {
            **_tp(d_estacion["item"]),
            "red": d_estacion["item"].get("red"),
            "distancia_m": d_estacion["ruta"]["distancia_m"],
            "duracion_min": _minutos(d_estacion["ruta"]["duracion_s"]),
            "modo": "caminando" if d_estacion["modo"] == "foot" else "vehiculo",
        }

    # --- Acceso al terreno -----------------------------------------------------------------
    acceso = None
    if frontal:
        ancho, fuente_ancho = cl.ancho_estimado(frontal["tags"])
        recta_frontal = geom_terreno.distance(frontal["linea"])
        if frontal["clase"] != "peatonal" and frontal["tags"].get("access") not in ("no", "private"):
            vehicular = "Sí"
        elif frontal_vehicular and geom_terreno.distance(frontal_vehicular["linea"]) <= recta_frontal + 25:
            vehicular = "Sí"
        else:
            vehicular = "No directo (vía peatonal)"
        acceso = {
            "tipo_via_frontal": cl.ETIQUETAS[frontal["clase"]],
            "clase_via_frontal": frontal["clase"],
            "via_frontal": cl.abreviar_nombre(frontal["nombre"] or "Vía sin nombre"),
            "distancia_via_m": round(recta_frontal),
            "ancho_aprox_m": ancho,
            "ancho_fuente": fuente_ancho,
            "carriles": frontal["tags"].get("lanes"),
            "superficie": frontal["tags"].get("surface"),
            "acceso_vehicular": vehicular,
            "transporte_publico": (
                f"Paradero a {_texto_distancia(transporte['paradero_cercano']['distancia_m'])}"
                if transporte["paradero_cercano"]
                else "Sin paraderos registrados en 1.5 km"
            ),
        }

    observaciones = _observaciones(
        {d["clase"]: d for d in destinos}, frontal, geom_terreno, vias, transporte
    )

    return {
        "punto": {"lat": lat, "lon": lon},
        "red_vial_cercana": red_vial,
        "observaciones": observaciones,
        "acceso": acceso,
        "transporte": transporte,
        "vias_geojson": _geojson(vias),
        "resumen": {c: sum(1 for v in vias if v["clase"] == c) for c in cl.CLASES},
        "meta": {
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fuentes": ["OpenStreetMap (Overpass)", "OSRM / FOSSGIS"],
            "nota_tiempos": "Tiempos por red vial real sin tráfico (OSRM).",
        },
    }


def _observaciones(por_clase: dict, frontal, geom_terreno, vias, transporte) -> list[dict]:
    obs: list[dict] = []

    def add(tipo: str, texto: str, detalle: str | None = None):
        obs.append({"tipo": tipo, "texto": texto, "detalle": detalle})

    art = por_clase.get("arterial")
    if art and art["recta_m"] <= 500:
        add("positivo", "Buena conexión con vías arteriales",
            f"{cl.abreviar_nombre(art['via']['nombre'] or 'Vía arterial')} a {_texto_distancia(art['ruta']['distancia_m'])}")
    elif art and art["recta_m"] <= 1200:
        add("neutral", "Conexión moderada con vías arteriales",
            f"{cl.abreviar_nombre(art['via']['nombre'] or 'Vía arterial')} a {_texto_distancia(art['ruta']['distancia_m'])}")
    else:
        add("alerta", "Lejos de vías arteriales", "No hay arteriales a menos de 1.2 km")

    exp = por_clase.get("expresa")
    if exp and _minutos(exp["ruta"]["duracion_s"]) <= 10:
        add("positivo", "Acceso rápido a vía expresa",
            f"{cl.abreviar_nombre(exp['via']['nombre'] or 'Vía expresa')} a {_minutos(exp['ruta']['duracion_s'])} min")
    elif exp:
        add("alerta", "Vía expresa a más de 10 min",
            f"{cl.abreviar_nombre(exp['via']['nombre'] or 'Vía expresa')} a {_minutos(exp['ruta']['duracion_s'])} min")
    else:
        add("alerta", "Sin vías expresas en 5 km")

    tp = transporte.get("paradero_cercano")
    if tp and tp["distancia_m"] <= 400:
        add("positivo", "Transporte público cercano",
            f"Paradero {tp['nombre'] or ''} a {_texto_distancia(tp['distancia_m'])}".replace("  ", " "))
    elif tp:
        add("alerta", "Transporte público a más de 400 m", f"Paradero a {_texto_distancia(tp['distancia_m'])}")
    else:
        add("alerta", "Sin paraderos registrados cerca")

    est = transporte.get("estacion_cercana")
    if est and est["distancia_m"] <= 2500:
        nombre = (est["nombre"] or "").removeprefix("Estación ").strip() or "cercana"
        add("positivo", f"Cerca de estación del {ETIQUETA_ESTACION[est['tipo']]}",
            f"{nombre} a {_texto_distancia(est['distancia_m'])} ({est['duracion_min']} min "
            f"{'caminando' if est['modo'] == 'caminando' else 'en vehículo'})")

    # Vías expresas/arteriales a menos de 300 m, ordenadas por distancia
    principales = [
        (geom_terreno.distance(v["linea"]), v) for v in vias if v["clase"] in ("expresa", "arterial")
    ]
    principales = sorted((p for p in principales if p[0] <= 300), key=lambda p: p[0])
    if (frontal and frontal["clase"] in ("expresa", "arterial")) or principales:
        nombre = principales[0][1]["nombre"] if principales else frontal["nombre"]
        add("alerta", "Tráfico elevado en hora punta",
            f"Estimado por cercanía a {cl.abreviar_nombre(nombre or 'vía principal')}")
    else:
        col = por_clase.get("colectora")
        if col and col["recta_m"] <= 150:
            add("neutral", "Tráfico moderado en el entorno", "Vía colectora a menos de 150 m")
        else:
            add("positivo", "Entorno de tráfico bajo", "Predominan vías locales")

    ruido = any(
        (v["clase"] == "expresa" and d <= 250) or (v["clase"] == "arterial" and d <= 120)
        for d, v in principales
    )
    if ruido:
        add("alerta", "Exposición potencial a ruido", "Vía expresa o arterial muy próxima")

    orden = {"positivo": 0, "neutral": 1, "alerta": 2}
    obs.sort(key=lambda o: orden[o["tipo"]])
    return obs


def _geojson(vias: list[dict]) -> dict:
    feats = []
    for v in vias:
        if v["clase"] not in cl.CLASES:
            continue
        feats.append(
            {
                "type": "Feature",
                "properties": {
                    "id": v["id"],
                    "clase": v["clase"],
                    "highway": v["highway"],
                    "nombre": cl.abreviar_nombre(v["nombre"]) if v["nombre"] else None,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[round(g["lon"], 6), round(g["lat"], 6)] for g in v["geometry"]],
                },
            }
        )
    # Se dibujan primero las locales para que las principales queden encima
    orden = {c: i for i, c in enumerate(reversed(cl.CLASES))}
    feats.sort(key=lambda f: orden[f["properties"]["clase"]])
    return {"type": "FeatureCollection", "features": feats}

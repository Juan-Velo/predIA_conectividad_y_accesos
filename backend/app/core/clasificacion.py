"""Clasificación de vías OSM según la jerarquía vial usada en Lima."""

CLASES = ("expresa", "arterial", "colectora", "local")

ETIQUETAS = {
    "expresa": "Vía expresa",
    "arterial": "Vía arterial",
    "colectora": "Vía colectora",
    "local": "Vía local",
    "servicio": "Vía de servicio",
    "peatonal": "Vía peatonal",
}

_HIGHWAY_A_CLASE = {
    "motorway": "expresa",
    "motorway_link": "expresa",
    "trunk": "expresa",
    "trunk_link": "expresa",
    "primary": "arterial",
    "primary_link": "arterial",
    "secondary": "colectora",
    "secondary_link": "colectora",
    "tertiary": "colectora",
    "tertiary_link": "colectora",
    "residential": "local",
    "unclassified": "local",
    "living_street": "local",
    "service": "servicio",
    "track": "servicio",
    "pedestrian": "peatonal",
    "footway": "peatonal",
    "path": "peatonal",
    "steps": "peatonal",
}

# Ancho típico de la sección vial (calzada + veredas) en Lima, en metros,
# usado solo cuando OSM no tiene `width` ni `lanes`.
_ANCHO_TIPICO_M = {
    "motorway": 40,
    "trunk": 30,
    "primary": 24,
    "secondary": 18,
    "tertiary": 14,
    "residential": 10,
    "unclassified": 10,
    "living_street": 7,
    "service": 6,
    "track": 5,
    "pedestrian": 5,
    "footway": 3,
    "path": 2,
    "steps": 2,
}


def clase_de(highway: str) -> str | None:
    return _HIGHWAY_A_CLASE.get(highway)


def es_enlace(highway: str) -> bool:
    return highway.endswith("_link")


def _num(valor: str | None) -> float | None:
    if not valor:
        return None
    try:
        return float(valor.replace(",", ".").split()[0].rstrip("m"))
    except (ValueError, IndexError):
        return None


def ancho_estimado(tags: dict) -> tuple[int, str]:
    """Devuelve (ancho en m, fuente) con fuente en {'osm', 'carriles', 'tipico'}."""
    ancho = _num(tags.get("width")) or _num(tags.get("est_width"))
    if ancho:
        return round(ancho), "osm"
    carriles = _num(tags.get("lanes"))
    if carriles:
        # 3.3 m por carril + ~2 m de vereda a cada lado
        return round(carriles * 3.3 + 4), "carriles"
    return _ANCHO_TIPICO_M.get(tags.get("highway", ""), 8), "tipico"


def abreviar_nombre(nombre: str) -> str:
    """'Avenida Defensores del Morro' -> 'Av. Defensores del Morro'."""
    reemplazos = [
        ("Avenida ", "Av. "),
        ("Jirón ", "Jr. "),
        ("Jiron ", "Jr. "),
        ("Pasaje ", "Psje. "),
        ("Prolongación ", "Prol. "),
        ("Carretera ", "Carr. "),
    ]
    for largo, corto in reemplazos:
        if nombre.startswith(largo):
            return corto + nombre[len(largo):]
    return nombre

"""Utilidades geométricas en una proyección local en metros.

Para áreas de unos pocos km una proyección equirectangular centrada en el
punto de estudio tiene error < 0.1 %, suficiente para distancias y áreas.
"""
import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points

M_POR_GRADO_LAT = 110_574.0
M_POR_GRADO_LON_ECUADOR = 111_320.0


class ProyeccionLocal:
    def __init__(self, lat0: float, lon0: float):
        self.lat0 = lat0
        self.lon0 = lon0
        self.kx = M_POR_GRADO_LON_ECUADOR * math.cos(math.radians(lat0))
        self.ky = M_POR_GRADO_LAT

    def xy(self, lat: float, lon: float) -> tuple[float, float]:
        return ((lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky)

    def latlon(self, x: float, y: float) -> tuple[float, float]:
        return (self.lat0 + y / self.ky, self.lon0 + x / self.kx)

    def punto(self, lat: float, lon: float) -> Point:
        return Point(self.xy(lat, lon))

    def linea(self, geometry: list[dict]) -> LineString | None:
        pts = [self.xy(g["lat"], g["lon"]) for g in geometry]
        return LineString(pts) if len(pts) >= 2 else None

    def poligono(self, latlons: list[tuple[float, float]]) -> Polygon | None:
        pts = [self.xy(lat, lon) for lat, lon in latlons]
        if len(pts) < 3:
            return None
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if poly.area > 0 else None


def punto_mas_cercano(origen, destino) -> tuple[tuple[float, float], float]:
    """Punto de `destino` más cercano a `origen` (en xy) y la distancia en metros."""
    _, p = nearest_points(origen, destino)
    return (p.x, p.y), origen.distance(destino)

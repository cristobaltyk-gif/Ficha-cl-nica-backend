# core/geo_router.py
# Resuelve región geográfica desde coordenadas GPS
# Usado por BookingCerebro para filtrar profesionales por región

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi import APIRouter, Query

# ============================================================
# CONFIG
# ============================================================
REGIONES_PATH = Path("/data/regiones.geo.json")

router = APIRouter(
    prefix="/geo",
    tags=["Geo"],
)

# ============================================================
# HELPERS
# ============================================================
def _load_regiones() -> list:
    try:
        return json.loads(REGIONES_PATH.read_text(encoding="utf-8")).get("regiones", [])
    except Exception:
        return []


def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _centro_bbox(bbox: dict) -> tuple[float, float]:
    return (
        (bbox["latMin"] + bbox["latMax"]) / 2,
        (bbox["lonMin"] + bbox["lonMax"]) / 2,
    )


def resolver_region(lat: float, lon: float) -> dict | None:
    """
    Resuelve región desde coordenadas GPS.
    1) Busca dentro de bbox exacto
    2) Fallback: región más cercana
    """
    regiones = _load_regiones()
    if not regiones:
        return None

    # 1) Dentro de bbox
    for region in regiones:
        b = region["bbox"]
        if b["latMin"] <= lat <= b["latMax"] and b["lonMin"] <= lon <= b["lonMax"]:
            return {"id": region["id"], "nombre": region["nombre"]}

    # 2) Más cercana
    mejor    = None
    min_dist = float("inf")
    for region in regiones:
        c_lat, c_lon = _centro_bbox(region["bbox"])
        d = _distancia_km(lat, lon, c_lat, c_lon)
        if d < min_dist:
            min_dist = d
            mejor = region

    if mejor:
        return {"id": mejor["id"], "nombre": mejor["nombre"]}
    return None


# ============================================================
# ENDPOINT
# ============================================================
@router.get("/sede")
def get_sede_por_gps(
    lat: float = Query(..., description="Latitud GPS"),
    lon: float = Query(..., description="Longitud GPS"),
):
    """
    Recibe coordenadas GPS y devuelve la región correspondiente.
    Usado por el frontend para filtrar profesionales disponibles.
    """
    region = resolver_region(lat, lon)

    if not region:
        return {
            "ok":     False,
            "region": None,
        }

    return {
        "ok":     True,
        "region": region["id"],
        "nombre": region["nombre"],
                       }
  

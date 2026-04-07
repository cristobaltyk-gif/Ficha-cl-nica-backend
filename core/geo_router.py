# core/geo_router.py
# Resuelve región geográfica desde coordenadas GPS o IP
# Usado por BookingCerebro para filtrar profesionales por región

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Query, Request

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


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip:
        ip = getattr(request.client, "host", "") or ""
    return ip.replace("::ffff:", "")


def resolver_region(lat: float, lon: float) -> dict | None:
    """Resuelve región desde coordenadas GPS."""
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


async def _resolver_por_ip(ip: str) -> dict | None:
    """Resuelve región desde IP usando ipapi.co."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res  = await client.get(
                f"https://ipapi.co/{ip}/json/",
                headers={"User-Agent": "ICA-Backend/1.0"},
            )
            data = res.json()
        lat = data.get("latitude")
        lon = data.get("longitude")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return resolver_region(lat, lon)
    except Exception:
        pass
    return None


# ============================================================
# ENDPOINT
# ============================================================
@router.get("/sede")
async def get_sede_por_gps(
    request: Request,
    lat: Optional[float] = Query(None, description="Latitud GPS"),
    lon: Optional[float] = Query(None, description="Longitud GPS"),
):
    """
    Resuelve región desde GPS o IP.
    - Con coords → GPS
    - Sin coords → IP
    - Sin resultado → ok: false (frontend muestra mensaje de GPS)
    """
    # 1) GPS si viene
    if lat is not None and lon is not None:
        region = resolver_region(lat, lon)
        if region:
            return {"ok": True, "source": "gps", "region": region["id"], "nombre": region["nombre"]}

    # 2) Fallback por IP
    ip = _get_client_ip(request)
    if ip:
        region = await _resolver_por_ip(ip)
        if region:
            return {"ok": True, "source": "ip", "region": region["id"], "nombre": region["nombre"]}

    # 3) Sin resultado
    return {"ok": False, "source": None, "region": None, "nombre": None}

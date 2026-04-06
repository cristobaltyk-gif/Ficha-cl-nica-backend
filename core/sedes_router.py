# core/sedes_router.py
# Gestión de sedes por profesional
# Lee y escribe /data/sedes.json

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ============================================================
# CONFIG
# ============================================================
SEDES_PATH     = Path("/data/sedes.json")
REGIONES_PATH  = Path("/data/regiones.geo.json")
_LOCK          = Lock()

router = APIRouter(
    prefix="/geo/sedes",
    tags=["Sedes"],
)

# ============================================================
# SCHEMAS
# ============================================================
class CentroModel(BaseModel):
    centro:    str = ""
    direccion: str = ""

class SedesProfesionalModel(BaseModel):
    regiones: Dict[str, List[CentroModel]] = {}

# ============================================================
# HELPERS
# ============================================================
def _load_sedes() -> dict:
    try:
        if not SEDES_PATH.exists():
            return {}
        return json.loads(SEDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_sedes(data: dict) -> None:
    SEDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEDES_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def _load_regiones() -> list:
    try:
        if not REGIONES_PATH.exists():
            return []
        return json.loads(REGIONES_PATH.read_text(encoding="utf-8")).get("regiones", [])
    except Exception:
        return []

# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/regiones")
def get_regiones():
    """Devuelve todas las regiones disponibles para el selector del admin."""
    regiones = _load_regiones()
    return [{"id": r["id"], "nombre": r["nombre"]} for r in regiones]


@router.get("/{pid}")
def get_sedes_profesional(pid: str):
    """Devuelve las sedes de un profesional."""
    sedes = _load_sedes()
    return sedes.get(pid) or {"regiones": {}}


@router.put("/{pid}")
def update_sedes_profesional(pid: str, data: SedesProfesionalModel):
    """
    Actualiza las sedes de un profesional.
    Reemplaza completamente sus regiones.
    """
    with _LOCK:
        sedes = _load_sedes()
        sedes[pid] = data.dict()
        _save_sedes(sedes)
    return {"ok": True, "pid": pid}


@router.delete("/{pid}")
def delete_sedes_profesional(pid: str):
    """Elimina todas las sedes de un profesional."""
    with _LOCK:
        sedes = _load_sedes()
        if pid not in sedes:
            raise HTTPException(status_code=404, detail="Profesional no tiene sedes")
        del sedes[pid]
        _save_sedes(sedes)
    return {"ok": True, "pid": pid}
  

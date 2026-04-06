from fastapi import APIRouter, HTTPException
from core.professionals_store import (
    list_professionals,
    add_professional,
    update_professional,
    delete_professional,
)
import json
from pathlib import Path
from typing import Optional

SEDES_PATH = Path("/data/sedes.json")

router = APIRouter(prefix="/professionals", tags=["professionals"])


# ==========================
# HELPERS
# ==========================
def _load_sedes() -> dict:
    try:
        if not SEDES_PATH.exists():
            return {}
        return json.loads(SEDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _filtrar_por_region(professionals: list, region: str) -> list:
    """
    Filtra profesionales según la región.
    Usa sedes.json — mismo ID que professionals.json.
    Si no hay sedes configuradas, devuelve todos (fallback).
    """
    sedes = _load_sedes()
    if not sedes:
        return professionals

    resultado = []
    for p in professionals:
        pid        = p.get("id") or ""
        sede_prof  = sedes.get(pid) or {}
        regiones   = sede_prof.get("regiones") or {}
        if region in regiones:
            resultado.append(p)

    # Si nadie atiende en esa región → devolver todos (fallback seguro)
    return resultado if resultado else professionals


# ==========================
# GET
# ==========================
@router.get("")
def get_all(public: bool = False, region: Optional[str] = None):
    profs = list_professionals(only_public=public)
    if region:
        profs = _filtrar_por_region(profs, region)
    return profs


# ==========================
# POST (admin agrega)
# ==========================
@router.post("")
def create(professional: dict):
    try:
        return add_professional(professional)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================
# PUT (admin edita)
# ==========================
@router.put("/{pid}")
def update(pid: str, updates: dict):
    try:
        return update_professional(pid, updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================
# DELETE (admin borra)
# ==========================
@router.delete("/{pid}")
def remove(pid: str):
    try:
        return delete_professional(pid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        

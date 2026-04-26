"""
admin/data_map_router.py
------------------------
Endpoint de diagnóstico — mapea toda la estructura de /data
sin exponer datos sensibles.

Uso: GET /admin/data-map
     Header: Authorization: Bearer <token_admin>
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from auth.auth_service import get_current_user  # ajusta si tu import es distinto

router = APIRouter(prefix="/admin", tags=["Admin"])

DATA_DIR = Path("/data")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sizeof_fmt(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _sample_keys(obj: Any, max_depth: int = 2) -> Any:
    """Devuelve solo las claves de un dict/list, sin valores sensibles."""
    if max_depth == 0:
        return "..."
    if isinstance(obj, dict):
        return {k: _sample_keys(v, max_depth - 1) for k, v in list(obj.items())[:5]}
    if isinstance(obj, list):
        if not obj:
            return []
        return [_sample_keys(obj[0], max_depth - 1), f"... ({len(obj)} items)"]
    # Valor escalar → solo tipo
    return type(obj).__name__


def _analyze_json(path: Path) -> Dict[str, Any]:
    """Analiza un archivo JSON y retorna metadata sin datos sensibles."""
    try:
        size = path.stat().st_size
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            count = len(data)
            structure = _sample_keys(data)
            dtype = "object"
        elif isinstance(data, list):
            count = len(data)
            structure = _sample_keys(data)
            dtype = "array"
        else:
            count = 1
            structure = type(data).__name__
            dtype = "scalar"

        return {
            "size":      _sizeof_fmt(size),
            "type":      dtype,
            "count":     count,
            "structure": structure,
            "error":     None,
        }
    except Exception as e:
        return {
            "size":      _sizeof_fmt(path.stat().st_size) if path.exists() else "?",
            "type":      "error",
            "count":     0,
            "structure": {},
            "error":     str(e),
        }


def _map_directory(directory: Path) -> Dict[str, Any]:
    """Recorre recursivamente un directorio y mapea su contenido."""
    result = {}

    if not directory.exists():
        return {"error": f"{directory} no existe"}

    for item in sorted(directory.iterdir()):
        if item.is_file():
            if item.suffix == ".json":
                result[item.name] = _analyze_json(item)
            else:
                result[item.name] = {
                    "size": _sizeof_fmt(item.stat().st_size),
                    "type": item.suffix or "file",
                }
        elif item.is_dir():
            # Para directorios de pacientes (muchos subdirs), resumir
            subdirs = [x for x in item.iterdir() if x.is_dir()]
            files   = [x for x in item.iterdir() if x.is_file()]

            if len(subdirs) > 10:
                # Es un directorio con muchos registros (ej: /data/pacientes)
                sample_dir  = subdirs[0] if subdirs else None
                sample_data = {}
                if sample_dir:
                    sample_data = {
                        f.name: _analyze_json(f) if f.suffix == ".json" else f.suffix
                        for f in sorted(sample_dir.iterdir())[:5]
                    }

                result[item.name] = {
                    "type":            "directory_records",
                    "total_records":   len(subdirs),
                    "direct_files":    [f.name for f in files],
                    "sample_record":   sample_dir.name if sample_dir else None,
                    "sample_structure": sample_data,
                }
            else:
                result[item.name] = _map_directory(item)

    return result


def _count_totals(mapped: Dict[str, Any]) -> Dict[str, int]:
    """Cuenta totales globales para el resumen."""
    totals = {"json_files": 0, "directories": 0, "records": 0}

    def _walk(obj):
        if not isinstance(obj, dict):
            return
        if obj.get("type") == "directory_records":
            totals["directories"] += 1
            totals["records"] += obj.get("total_records", 0)
            return
        if "structure" in obj and "count" in obj:
            totals["json_files"] += 1
            return
        for v in obj.values():
            _walk(v)

    _walk(mapped)
    return totals


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.get("/data-map")
def get_data_map(current_user: dict = Depends(get_current_user)):
    """
    Mapea toda la estructura de /data.
    Solo accesible por usuarios con rol admin.
    """
    # Verificar rol admin
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")

    mapped = _map_directory(DATA_DIR)
    totals = _count_totals(mapped)

    return {
        "data_dir":  str(DATA_DIR),
        "summary":   totals,
        "structure": mapped,
    }


@router.get("/data-map/files")
def list_all_json_files(current_user: dict = Depends(get_current_user)):
    """
    Lista plana de todos los archivos JSON con su tamaño.
    Útil para planificar la migración.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")

    files = []
    total_size = 0

    for json_file in sorted(DATA_DIR.rglob("*.json")):
        size = json_file.stat().st_size
        total_size += size
        files.append({
            "path":     str(json_file.relative_to(DATA_DIR)),
            "size":     _sizeof_fmt(size),
            "size_bytes": size,
        })

    return {
        "total_files": len(files),
        "total_size":  _sizeof_fmt(total_size),
        "files":       files,
    }
    

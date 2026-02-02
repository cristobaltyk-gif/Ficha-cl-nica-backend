from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Depends

# 🔐 AUTH INTERNO (SEPARADO DEL LOGIN)
from auth.internal_auth import require_internal_auth

# ==================================================
# CONFIGURACIÓN CANÓNICA
# ==================================================
BASE_DATA_PATH = Path("data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa"],
    dependencies=[Depends(require_internal_auth)]
)

# ==================================================
# HELPERS
# ==================================================
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


def admin_file(rut: str) -> Path:
    return patient_dir(rut) / "admin.json"


def build_admin_ficha(
    data: Dict[str, Any],
    created_at: str | None = None
) -> Dict[str, Any]:
    now = utc_now()
    return {
        "rut": data["rut"],
        "nombre": data["nombre"],
        "apellido_paterno": data.get("apellido_paterno", ""),
        "apellido_materno": data.get("apellido_materno", ""),
        "fecha_nacimiento": data.get("fecha_nacimiento"),
        "sexo": data.get("sexo"),
        "telefono": data.get("telefono"),
        "email": data.get("email"),
        "direccion": data.get("direccion"),
        "prevision": data.get("prevision"),
        "created_at": created_at or now,
        "updated_at": now
    }

# ==================================================
# ENDPOINTS (PRIVADOS – AUTH INTERNO)
# ==================================================

@router.post("")
def create_or_update_ficha_administrativa(
    data: Dict[str, Any],
    auth=Depends(require_internal_auth)
):
    """
    Crea o actualiza la FICHA ADMINISTRATIVA.
    NO incluye datos clínicos.
    """
    if "rut" not in data or "nombre" not in data:
        raise HTTPException(
            status_code=400,
            detail="Campos obligatorios: rut, nombre"
        )

    rut = data["rut"]

    with LOCK:
        BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
        pdir = patient_dir(rut)
        pdir.mkdir(exist_ok=True)

        file = admin_file(rut)

        created_at = None
        if file.exists():
            old = json.loads(file.read_text(encoding="utf-8"))
            created_at = old.get("created_at")

        ficha = build_admin_ficha(data, created_at)

        file.write_text(
            json.dumps(ficha, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
    }


@router.get("/{rut}")
def get_ficha_administrativa(
    rut: str,
    auth=Depends(require_internal_auth)
):
    """
    Obtiene ficha administrativa por RUT.
    """
    file = admin_file(rut)

    if not file.exists():
        raise HTTPException(
            status_code=404,
            detail="Ficha administrativa no encontrada"
        )

    return json.loads(file.read_text(encoding="utf-8"))


@router.get("/search")
def search_fichas_administrativas(
    q: str = Query(..., min_length=2),
    auth=Depends(require_internal_auth)
):
    """
    Búsqueda por rut / nombre / apellidos.
    """
    results: List[Dict[str, Any]] = []

    if not BASE_DATA_PATH.exists():
        return {"total": 0, "results": []}

    q = q.lower()

    for pdir in BASE_DATA_PATH.iterdir():
        file = pdir / "admin.json"
        if not file.exists():
            continue

        data = json.loads(file.read_text(encoding="utf-8"))

        haystack = " ".join([
            data.get("rut", ""),
            data.get("nombre", ""),
            data.get("apellido_paterno", ""),
            data.get("apellido_materno", "")
        ]).lower()

        if q in haystack:
            results.append(data)

    return {
        "total": len(results),
        "results": results
    }

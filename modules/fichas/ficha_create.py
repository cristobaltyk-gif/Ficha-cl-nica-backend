from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth

# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Create"],
    dependencies=[Depends(require_internal_auth)]
)

# ===============================
# HELPERS
# ===============================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut

def admin_file(rut: str) -> Path:
    return patient_dir(rut) / "admin.json"

# ===============================
# CREATE (CANÓNICO)
# ===============================

@router.post("")
def create_ficha_administrativa(data: Dict[str, Any]):
    """
    CREA ficha administrativa
    EXACTAMENTE con el contrato del frontend.
    """

    # ---------------------------
    # VALIDACIÓN DURA (CONTRATO)
    # ---------------------------
    required = [
        "rut",
        "nombre",
        "apellido_paterno",
        "fecha_nacimiento"
    ]

    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(
                status_code=400,
                detail=f"Campo obligatorio faltante: {field}"
            )

    rut = data["rut"]

    # ---------------------------
    # LOCK DE ESCRITURA
    # ---------------------------
    with LOCK:
        BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)

        pdir = patient_dir(rut)
        pdir.mkdir(exist_ok=True)

        file = admin_file(rut)

        if file.exists():
            raise HTTPException(
                status_code=409,
                detail="Ficha administrativa ya existe"
            )

        # ---------------------------
        # FICHA ADMINISTRATIVA (CONTRATO ÚNICO)
        # ---------------------------
        ficha = {
            "rut": rut,
            "nombre": data["nombre"],
            "apellido_paterno": data["apellido_paterno"],
            "apellido_materno": data.get("apellido_materno", ""),
            "fecha_nacimiento": data["fecha_nacimiento"],
            "direccion": data.get("direccion", ""),
            "telefono": data.get("telefono", ""),
            "email": data.get("email", ""),
            "prevision": data.get("prevision", ""),
            "created_at": utc_now(),
            "updated_at": utc_now()
        }

        file.write_text(
            json.dumps(ficha, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
    }

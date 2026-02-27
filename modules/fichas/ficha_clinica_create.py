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

BASE_DATA_PATH = Path("/data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/clinica",
    tags=["Ficha Clínica - Create"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


def events_dir(rut: str) -> Path:
    return patient_dir(rut) / "eventos"


# ===============================
# CREATE EVENTO CLÍNICO
# ===============================

@router.post("")
def create_ficha_clinica(
    data: Dict[str, Any],
    user=Depends(require_internal_auth)
):
    """
    CREA evento clínico dentro de /data/pacientes/{rut}/eventos/
    EXACTAMENTE con el contrato del frontend.
    """

    required = ["rut", "fecha", "hora"]

    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(
                status_code=400,
                detail=f"Campo obligatorio faltante: {field}"
            )

    rut = data["rut"]

    with LOCK:
        patient_path = patient_dir(rut)

        if not patient_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Paciente no tiene ficha administrativa"
            )

        edir = events_dir(rut)
        edir.mkdir(exist_ok=True)

        filename = f"{data['fecha']}_{data['hora'].replace(':','-')}.json"
        file = edir / filename

        if file.exists():
            raise HTTPException(
                status_code=409,
                detail="Ya existe evento clínico en esa fecha y hora"
            )

        # Mantener exactamente los campos del frontend
        evento = data.copy()

        # Trazabilidad profesional
        evento["professional_id"] = user["usuario"]
        evento["professional_name"] = user["role"]["name"]
        evento["created_at"] = utc_now()
        evento["version"] = 1

        file.write_text(
            json.dumps(evento, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
  }

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
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Evento"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# GUARDAR EVENTO CLÍNICO
# ===============================

@router.post("")
def save_clinical_event(
    data: Dict[str, Any],
    user=Depends(require_internal_auth)
):
    """
    Guarda un JSON clínico dentro de la carpeta del paciente.
    No crea ficha.
    No modifica admin.
    Solo agrega un evento.
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
        pdir = patient_dir(rut)

        if not pdir.exists():
            raise HTTPException(
                status_code=404,
                detail="La ficha del paciente no existe"
            )

        events_dir = pdir / "eventos"
        events_dir.mkdir(exist_ok=True)

        filename = f"{data['fecha']}_{data['hora'].replace(':','-')}.json"
        file = events_dir / filename

        if file.exists():
            raise HTTPException(
                status_code=409,
                detail="Ya existe una atención en esa fecha y hora"
            )

        evento = data.copy()

        # Trazabilidad profesional
        evento["professional_id"] = user["usuario"]
        evento["professional_name"] = user["role"]["name"]
        evento["created_at"] = utc_now()

        file.write_text(
            json.dumps(evento, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
    }

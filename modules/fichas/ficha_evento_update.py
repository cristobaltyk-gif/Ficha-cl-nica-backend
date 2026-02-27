from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth
from modules.fichas.ficha_evento_schema import FichaEventoCreate


# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Update"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def chile_today() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).date().isoformat()


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# MODIFICAR EVENTO CLÍNICO
# ===============================

@router.put("")
def update_clinical_event(
    data: FichaEventoCreate,
    user=Depends(require_internal_auth)
):
    """
    Modifica un evento clínico SOLO si fue creado hoy (fecha Chile).
    """

    rut = data.rut

    with LOCK:
        pdir = patient_dir(rut)

        if not pdir.exists():
            raise HTTPException(
                status_code=404,
                detail="La ficha del paciente no existe"
            )

        events_dir = pdir / "eventos"

        filename = f"{data.fecha}_{data.hora.replace(':','-')}.json"
        file = events_dir / filename

        if not file.exists():
            raise HTTPException(
                status_code=404,
                detail="Evento clínico no encontrado"
            )

        # Leer evento actual
        evento_actual = json.loads(file.read_text(encoding="utf-8"))

        # Verificar fecha creación
        created_at = evento_actual.get("created_at")
        if not created_at:
            raise HTTPException(
                status_code=400,
                detail="Evento sin timestamp válido"
            )

        created_date = created_at.split("T")[0]

        if created_date != chile_today():
            raise HTTPException(
                status_code=403,
                detail="Solo se pueden modificar eventos creados hoy"
            )

        # Actualizar SOLO campos clínicos
        evento_actual.update(data.dict())

        # NO se cambia professional_id
        # NO se cambia professional_name
        # NO se cambia created_at

        file.write_text(
            json.dumps(evento_actual, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
    }

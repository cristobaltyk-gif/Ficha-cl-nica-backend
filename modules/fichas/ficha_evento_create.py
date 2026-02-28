from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth
from modules.fichas.ficha_evento_schema import FichaEventoCreate
from agenda.store import set_slot

# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")
PROFESSIONALS_FILE = Path("/data/professionals.json")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Evento"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def chile_now() -> str:
    """
    Fecha y hora oficial Chile
    """
    return datetime.now(ZoneInfo("America/Santiago")).isoformat()


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# GUARDAR EVENTO CLÍNICO
# ===============================

@router.post("")
def save_clinical_event(
    data: FichaEventoCreate,
    user=Depends(require_internal_auth)
):
    """
    Guarda un JSON clínico dentro de:
    /data/pacientes/{rut}/eventos/

    - No crea ficha administrativa
    - No modifica admin.json
    - Solo agrega una atención
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
        events_dir.mkdir(exist_ok=True)

        filename = f"{data.fecha}_{data.hora.replace(':','-')}.json"
        file = events_dir / filename

        if file.exists():
            raise HTTPException(
                status_code=409,
                detail="Ya existe una atención en esa fecha y hora"
            )

        # Datos clínicos (exactamente tu esquema)
        evento = data.dict()

        professional_id = user["usuario"]

        # Leer profesionales desde JSON real
        if not PROFESSIONALS_FILE.exists():
            raise HTTPException(status_code=500, detail="Archivo de profesionales no encontrado")

        professionals = json.loads(PROFESSIONALS_FILE.read_text(encoding="utf-8"))

        if professional_id not in professionals:
            raise HTTPException(status_code=403, detail="Profesional no válido")

        evento["professional_id"] = professional_id
        evento["professional_name"] = professionals[professional_id]["name"]

        # Timestamp Chile oficial
        evento["created_at"] = chile_now()

        file.write_text(
            json.dumps(evento, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        # ===============================
        # Marcar slot como evaluado
        # ===============================
        set_slot(
            date=data.fecha,
            time=data.hora,
            professional=user["usuario"],  # backend es la verdad
            status="evaluated",
            rut=rut    
        )
        return {
            "status": "ok",
            "rut": rut
        }

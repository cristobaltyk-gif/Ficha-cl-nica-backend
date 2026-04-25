from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from modules.fichas.ficha_evento_schema import FichaEventoCreate
from agenda.store import set_slot
from db.supabase_client import get_paciente, create_evento

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Evento"],
    dependencies=[Depends(require_internal_auth)]
)


def chile_now() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).isoformat()


@router.post("")
def save_clinical_event(
    data: FichaEventoCreate,
    user=Depends(require_internal_auth)
):
    rut = data.rut

    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="La ficha del paciente no existe")

    evento = data.dict()
    evento["professional_id"]   = user["professional"]
    evento["professional_user"] = user["usuario"]
    evento["professional_role"] = user["role"]
    evento["created_at"]        = chile_now()

    try:
        create_evento(rut, evento)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    set_slot(
        date=data.fecha,
        time=data.hora,
        professional=user["usuario"],
        status="evaluated",
        rut=rut
    )

    return {"status": "ok", "rut": rut}

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from modules.fichas.ficha_evento_schema import FichaEventoCreate
from agenda.store import set_slot
from db.supabase_client import get_paciente, create_evento, _get_conn

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Evento"],
    dependencies=[Depends(require_internal_auth)]
)


def chile_now() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).isoformat()


def _migrar_fotos_slot_a_evento(rut: str, fecha: str, hora: str) -> dict:
    """
    Lee fotos_dermatologia del slot y las retorna para incluir en el evento.
    Luego limpia el slot.
    """
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT extra FROM slots WHERE date=%s AND time=%s AND rut=%s",
                    (fecha, hora, rut)
                )
                row = cur.fetchone()
                if not row or not row["extra"]:
                    return {}

                extra = row["extra"] if isinstance(row["extra"], dict) else json.loads(row["extra"])
                fotos = extra.get("fotos_dermatologia", [])
                if not fotos:
                    return {}

                # Limpiar fotos del slot
                cur.execute("""
                    UPDATE slots SET extra = extra - 'fotos_dermatologia'
                    WHERE date=%s AND time=%s AND rut=%s
                """, (fecha, hora, rut))
                conn.commit()

                print(f"[DERMATOLOGIA] ✅ {len(fotos)} foto(s) migradas al evento de {rut}")
                return {"fotos_dermatologia": fotos}

    except Exception as e:
        print(f"[DERMATOLOGIA] Error migrando fotos: {e}")
        return {}


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

    # Migrar fotos de dermatología si existen
    fotos = _migrar_fotos_slot_a_evento(rut, data.fecha, data.hora)
    if fotos:
        evento.update(fotos)

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

from __future__ import annotations

import json
import psycopg2
import psycopg2.extras
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from modules.fichas.ficha_evento_schema import FichaEventoCreate
from db.supabase_client import get_paciente, _get_conn, _utc_now

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Update"],
    dependencies=[Depends(require_internal_auth)]
)


def chile_today() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).date().isoformat()


@router.put("")
def update_clinical_event(
    data: FichaEventoCreate,
    user=Depends(require_internal_auth)
):
    """
    Modifica un evento clínico SOLO si fue creado hoy (fecha Chile).
    """
    rut = data.rut
    fecha_hora = f"{data.fecha}_{data.hora.replace(':', '-')}"

    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="La ficha del paciente no existe")

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, contenido, created_at FROM eventos
                WHERE rut_paciente = %s AND fecha_hora = %s
            """, (rut, fecha_hora))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Evento clínico no encontrado")

            created_at = str(row["created_at"])
            created_date = created_at.split("T")[0][:10]

            if created_date != chile_today():
                raise HTTPException(
                    status_code=403,
                    detail="Solo se pueden modificar eventos creados hoy"
                )

            evento_actual = dict(row["contenido"])
            evento_actual.update(data.dict())

            cur.execute("""
                UPDATE eventos
                SET contenido = %s, updated_at = %s
                WHERE id = %s
            """, (json.dumps(evento_actual), _utc_now(), row["id"]))
            conn.commit()

    return {"status": "ok", "rut": rut}

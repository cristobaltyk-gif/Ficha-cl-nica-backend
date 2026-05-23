from __future__ import annotations

import base64
import json as _json
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form
from agenda import service
from agenda.models import (
    OccupancyResponse,
    CreateSlotRequest,
    ConfirmSlotRequest,
    CancelSlotRequest,
    RescheduleRequest,
    MutationResult,
)
from agenda.store import set_slot
from db.supabase_client import _get_conn

router = APIRouter(prefix="/agenda", tags=["agenda"])


# ======================================================
# LECTURAS
# ======================================================

@router.get("", summary="Agenda por día")
def get_agenda_day(date: str = Query(..., description="YYYY-MM-DD")):
    try:
        data = service.get_day(date)
        return {"date": date, "calendar": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/occupancy", response_model=OccupancyResponse, summary="Ocupación por hora")
def get_occupancy(
    date: str = Query(..., description="YYYY-MM-DD"),
    time: str = Query(..., description="HH:MM")
):
    try:
        professionals = service.get_occupancy(date, time)
        return OccupancyResponse(date=date, time=time, professionals=professionals)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# MUTACIONES
# ======================================================

@router.post("/create", response_model=MutationResult, summary="Crear / reservar slot")
def create_slot(payload: CreateSlotRequest):
    try:
        return service.create_slot(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm", response_model=MutationResult, summary="Confirmar slot reservado")
def confirm_slot(payload: ConfirmSlotRequest):
    try:
        return service.confirm_slot(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel", response_model=MutationResult, summary="Anular slot")
def cancel_slot(payload: CancelSlotRequest):
    try:
        return service.cancel_slot(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reschedule", response_model=MutationResult, summary="Reprogramar slot")
def reschedule_slot(payload: RescheduleRequest):
    try:
        return service.reschedule(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# DERMATOLOGÍA — FOTOS
# ======================================================

@router.post("/dermatologia/fotos", summary="Subir fotos dermatología al slot")
async def subir_fotos_dermatologia(
    rut:          str        = Form(...),
    date:         str        = Form(...),
    time:         str        = Form(...),
    professional: str        = Form(...),
    foto1:        UploadFile = File(None),
    comentario1:  str        = Form(""),
    foto2:        UploadFile = File(None),
    comentario2:  str        = Form(""),
):
    try:
        fotos = []
        for foto, comentario in [(foto1, comentario1), (foto2, comentario2)]:
            if foto and foto.filename:
                contenido = await foto.read()
                fotos.append({
                    "data":       base64.b64encode(contenido).decode("utf-8"),
                    "comentario": comentario,
                })

        # Leer extra actual del slot
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT extra, status FROM slots WHERE date=%s AND time=%s AND professional=%s",
                    (date, time, professional)
                )
                row = cur.fetchone()
                extra  = dict(row["extra"]) if row and row["extra"] else {}
                status = row["status"] if row else "reserved"

        extra["fotos_dermatologia"] = fotos

        set_slot(
            date=date, time=time, professional=professional,
            status=status, rut=rut, extra=extra
        )

        return {"ok": True, "fotos": len(fotos)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dermatologia/fotos", summary="Obtener fotos dermatología del slot")
def get_fotos_dermatologia(
    rut:  str = Query(...),
    date: str = Query(...),
    time: str = Query(...),
):
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT extra FROM slots WHERE date=%s AND time=%s AND rut=%s",
                    (date, time, rut)
                )
                row = cur.fetchone()

        if not row or not row["extra"]:
            return {"fotos": []}

        extra = row["extra"] if isinstance(row["extra"], dict) else _json.loads(row["extra"])
        return {"fotos": extra.get("fotos_dermatologia", [])}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

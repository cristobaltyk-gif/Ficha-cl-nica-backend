from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from agenda import service
from agenda.models import (
    OccupancyResponse,
    CreateSlotRequest,
    ConfirmSlotRequest,
    CancelSlotRequest,
    RescheduleRequest,
    MutationResult,
)

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
        

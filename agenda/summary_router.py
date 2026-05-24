from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from agenda import summary_service

router = APIRouter(
    prefix="/agenda/summary",
    tags=["agenda-summary"]
)

@router.get("/month", summary="Resumen 30 días por profesional desde start_date")
def get_month_summary(
    professional: str = Query(...),
    start_date:   Optional[str] = Query(None),
    month:        Optional[str] = Query(None),
    tipo:         Optional[str] = Query(None, description="presencial | telemedicina"),
):
    try:
        if start_date:
            return summary_service.range_summary(
                professional=professional,
                start_date=start_date,
                days=30,
                tipo=tipo,
            )
        if not month:
            raise HTTPException(status_code=422, detail="Debe enviar 'start_date' o 'month'")
        return summary_service.month_summary(professional=professional, month=month)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/week", summary="Resumen 7 días por profesional desde start_date")
def get_week_summary(
    professional: str = Query(...),
    start_date:   Optional[str] = Query(None),
    week_start:   Optional[str] = Query(None),
    tipo:         Optional[str] = Query(None, description="presencial | telemedicina"),
):
    try:
        if start_date:
            return summary_service.range_summary(
                professional=professional,
                start_date=start_date,
                days=7,
                tipo=tipo,
            )
        if not week_start:
            raise HTTPException(status_code=422, detail="Debe enviar 'start_date' o 'week_start'")
        return summary_service.week_summary(professional=professional, week_start=week_start)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

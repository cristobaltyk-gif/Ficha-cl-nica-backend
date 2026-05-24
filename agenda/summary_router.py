from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from agenda import summary_service

# ======================================================
# SUMMARY ROUTER — ICA
# ------------------------------------------------------
# ✔ Solo lectura
# ✔ No muta agenda
# ✔ start_date ES la fecha de inicio (tal cual la envía el frontend)
# ✔ /month devuelve 30 días desde start_date
# ✔ /week devuelve 7 días desde start_date
# ✔ Compatible con contrato legacy (month / week_start)
# ======================================================

router = APIRouter(
    prefix="/agenda/summary",
    tags=["agenda-summary"]
)

# ======================================================
# 📅 SUMMARY "MENSUAL" → 30 DÍAS DESDE start_date
# ======================================================

@router.get("/month", summary="Resumen 30 días por profesional desde start_date")
def get_month_summary(
    professional: str = Query(..., description="ID profesional (ej: medico1)"),
    start_date: Optional[str] = Query(
        None, description="Fecha inicio YYYY-MM-DD (ej: 2026-01-15)"
    ),
    month: Optional[str] = Query(
        None, description="Mes YYYY-MM (legacy)"
    ),
    tipo: Optional[str] = Query(
        None, description="Filtrar por tipo: presencial | telemedicina"
    ),
):
    """
    Devuelve estado por día a futuro (30 días) desde start_date:

    free  = muchas horas libres
    low   = pocas horas libres
    full  = sin cupos
    empty = día sin agenda definida
    """
    try:
        if start_date:
            return summary_service.range_summary(
                professional=professional,
                start_date=start_date,
                days=30,
                tipo=tipo,
            )

        if not month:
            raise HTTPException(
                status_code=422,
                detail="Debe enviar 'start_date' o 'month'"
            )

        return summary_service.month_summary(
            professional=professional,
            month=month
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# 🗓️ SUMMARY "SEMANAL" → 7 DÍAS DESDE start_date
# ======================================================

@router.get("/week", summary="Resumen 7 días por profesional desde start_date")
def get_week_summary(
    professional: str = Query(..., description="ID profesional (ej: medico1)"),
    start_date: Optional[str] = Query(
        None, description="Fecha inicio YYYY-MM-DD (ej: 2026-01-15)"
    ),
    week_start: Optional[str] = Query(
        None, description="Lunes YYYY-MM-DD (legacy)"
    ),
    tipo: Optional[str] = Query(
        None, description="Filtrar por tipo: presencial | telemedicina"
    ),
):
    """
    Devuelve slots ocupados por día (7 días consecutivos) desde start_date.
    """
    try:
        if start_date:
            return summary_service.range_summary(
                professional=professional,
                start_date=start_date,
                days=7,
                tipo=tipo,
            )

        if not week_start:
            raise HTTPException(
                status_code=422,
                detail="Debe enviar 'start_date' o 'week_start'"
            )

        return summary_service.week_summary(
            professional=professional,
            week_start=week_start
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

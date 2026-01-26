from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from agenda import summary_service

# ======================================================
# SUMMARY ROUTER — ICA
# ------------------------------------------------------
# ✔ Solo lectura
# ✔ No muta agenda
# ✔ Para calendario mensual y semanal
# ======================================================

router = APIRouter(
    prefix="/agenda/summary",
    tags=["agenda-summary"]
)


# ======================================================
# 📅 SUMMARY MENSUAL (Secretaría / Paciente)
# ======================================================

@router.get("/month", summary="Resumen mensual por profesional")
def get_month_summary(
    professional: str = Query(..., description="ID profesional (ej: medico1)"),
    month: str = Query(..., description="Mes YYYY-MM (ej: 2026-01)")
):
    """
    Devuelve estado por día del mes:

    free  = muchas horas libres
    low   = pocas horas libres
    full  = sin cupos
    empty = día sin agenda definida
    """
    try:
        return summary_service.month_summary(
            professional=professional,
            month=month
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======================================================
# 🗓️ SUMMARY SEMANAL (Médico)
# ======================================================

@router.get("/week", summary="Resumen semanal por profesional")
def get_week_summary(
    professional: str = Query(..., description="ID profesional (ej: medico1)"),
    week_start: str = Query(..., description="Lunes YYYY-MM-DD (ej: 2026-01-26)")
):
    """
    Devuelve slots ocupados por día de la semana.
    Ideal para vista semanal del médico.
    """
    try:
        return summary_service.week_summary(
            professional=professional,
            week_start=week_start
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

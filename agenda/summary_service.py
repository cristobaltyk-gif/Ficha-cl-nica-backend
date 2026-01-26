from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Any

from agenda import store

# ======================================================
# CANÓNICO ICA — SUMMARY ENGINE
# ------------------------------------------------------
# ✔ Calcula disponibilidad mensual y semanal
# ✔ NO muta agenda
# ✔ SOLO lectura de agenda_future.json
# ✔ Preparado para paciente online booking
# ======================================================

# =============================
# Reglas de estado (OFICIAL)
# =============================

FREE_THRESHOLD = 10   # ≥10 slots libres → green
LOW_THRESHOLD = 1     # 1–9 slots libres → yellow
FULL_THRESHOLD = 0    # 0 slots libres → red


# =============================
# Helpers internos
# =============================

def _day_status(free_slots: int) -> str:
    """
    Traduce número de slots libres a estado canónico.
    """
    if free_slots >= FREE_THRESHOLD:
        return "free"
    if free_slots >= LOW_THRESHOLD:
        return "low"
    if free_slots == FULL_THRESHOLD:
        return "full"
    return "empty"


def _count_free_slots(day_data: Dict[str, Any], professional: str) -> int:
    """
    Cuenta slots disponibles para un profesional en un día.
    """
    prof = day_data.get(professional)

    # Día sin agenda definida
    if not prof:
        return -1

    slots = prof.get("slots", {})

    # Total de slots ocupados
    busy = len(slots)

    # Total de slots posibles (09:00–18:00 cada 15 min)
    total = 36  # 9 horas * 4 slots/hora

    free = total - busy
    return free


# ======================================================
# SUMMARY MENSUAL (Secretaría / Paciente)
# ======================================================

def month_summary(*, professional: str, month: str) -> Dict[str, Any]:
    """
    Devuelve estado por día del mes.

    month: "2026-01"
    """
    year, mm = month.split("-")
    year = int(year)
    mm = int(mm)

    # Primer día del mes
    current = date(year, mm, 1)

    # Último día (aprox)
    if mm == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, mm + 1, 1)

    days: Dict[str, str] = {}

    while current < next_month:
        iso = current.isoformat()

        day_data = store.read_day(iso)
        free_slots = _count_free_slots(day_data, professional)

        if free_slots == -1:
            status = "empty"
        else:
            status = _day_status(free_slots)

        days[iso] = status
        current += timedelta(days=1)

    return {
        "month": month,
        "professional": professional,
        "days": days
    }


# ======================================================
# SUMMARY SEMANAL (Médico)
# ======================================================

def week_summary(*, professional: str, week_start: str) -> Dict[str, Any]:
    """
    Devuelve agenda resumida por semana.

    week_start: "2026-01-26" (lunes)
    """
    start = date.fromisoformat(week_start)

    week: Dict[str, Dict[str, str]] = {}

    for i in range(7):
        current = start + timedelta(days=i)
        iso = current.isoformat()

        day_data = store.read_day(iso)
        prof = day_data.get(professional, {})

        slots = prof.get("slots", {})

        # Solo devolvemos status por hora
        day_slots = {
            time: slot.get("status", "available")
            for time, slot in slots.items()
        }

        week[iso] = day_slots

    return {
        "week_start": week_start,
        "professional": professional,
        "days": week
    }

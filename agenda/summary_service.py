from __future__ import annotations

from datetime import date, timedelta, datetime
from typing import Dict, Any
import json
from pathlib import Path

from agenda import store

# ======================================================
# CANÓNICO ICA — SUMMARY ENGINE (PRODUCCIÓN)
# ------------------------------------------------------
# ✔ Usa horario REAL del profesional
# ✔ Un día sin slots = DISPONIBLE si el médico trabaja
# ✔ Soporta rangos (7 / 30 días)
# ✔ NO muta agenda
# ✔ NO inventa datos
# ======================================================

# =============================
# Configuración
# =============================

PROFESSIONALS_PATH = Path("data/professionals.json")

FREE_THRESHOLD = 10   # ≥10 slots libres → green
LOW_THRESHOLD = 1     # 1–9 slots libres → yellow
FULL_THRESHOLD = 0    # 0 slots libres → red


# =============================
# Cargar profesionales (horario)
# =============================

def _load_professionals() -> Dict[str, Any]:
    if not PROFESSIONALS_PATH.exists():
        return {}

    with open(PROFESSIONALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


PROFESSIONALS = _load_professionals()


# =============================
# Helpers de estado
# =============================

def _day_status(free_slots: int) -> str:
    if free_slots >= FREE_THRESHOLD:
        return "free"
    if free_slots >= LOW_THRESHOLD:
        return "low"
    if free_slots == FULL_THRESHOLD:
        return "full"
    return "empty"


def _weekday_name(d: date) -> str:
    # monday, tuesday, ...
    return d.strftime("%A").lower()


def _build_slots_for_day(schedule: Dict[str, Any]) -> int:
    """
    Calcula TOTAL de slots posibles en el día
    soporta múltiples bloques (mañana / tarde)
    """
    total = 0
    slot_minutes = schedule.get("slotMinutes", 30)

    for block in schedule.get("blocks", []):
        start = datetime.strptime(block["start"], "%H:%M")
        end = datetime.strptime(block["end"], "%H:%M")
        minutes = int((end - start).total_seconds() / 60)
        total += minutes // slot_minutes

    return total


# =============================
# Conteo REAL de slots libres
# =============================

def _count_free_slots(day_data: Dict[str, Any], professional: str, current_date: date) -> int:
    """
    Devuelve cantidad de slots libres para ese día.
    - Si el médico NO trabaja ese día → -1 (empty)
    - Si trabaja y no hay slots → todos libres
    """

    prof_cfg = PROFESSIONALS.get(professional)
    if not prof_cfg or not prof_cfg.get("active"):
        return -1

    schedule = prof_cfg.get("schedule")
    if not schedule:
        return -1

    weekday = _weekday_name(current_date)
    day_schedule = schedule.get("days", {}).get(weekday)

    # No atiende ese día
    if not day_schedule:
        return -1

    total_slots = _build_slots_for_day(day_schedule)

    # Slots ocupados reales
    prof_day = day_data.get(professional, {})
    slots = prof_day.get("slots", {})
    busy = len(slots)

    free = total_slots - busy
    return max(free, 0)


# ======================================================
# SUMMARY POR RANGO (7 / 30 días)
# ======================================================

def range_summary(
    *,
    professional: str,
    start_date: str,
    days: int
) -> Dict[str, Any]:
    start = date.fromisoformat(start_date)

    result_days: Dict[str, str] = {}

    for i in range(days):
        current = start + timedelta(days=i)
        iso = current.isoformat()

        day_data = store.read_day(iso)
        free_slots = _count_free_slots(day_data, professional, current)

        if free_slots == -1:
            status = "empty"
        else:
            status = _day_status(free_slots)

        result_days[iso] = status

    return {
        "start_date": start_date,
        "professional": professional,
        "days": result_days
    }


# ======================================================
# LEGACY (no se rompe nada)
# ======================================================

def month_summary(*, professional: str, month: str) -> Dict[str, Any]:
    year, mm = month.split("-")
    year = int(year)
    mm = int(mm)

    start = date(year, mm, 1)
    days_in_month = (date(year + (mm == 12), (mm % 12) + 1, 1) - start).days

    return range_summary(
        professional=professional,
        start_date=start.isoformat(),
        days=days_in_month
    )


def week_summary(*, professional: str, week_start: str) -> Dict[str, Any]:
    return range_summary(
        professional=professional,
        start_date=week_start,
        days=7
    )

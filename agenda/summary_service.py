"""
agenda/summary_router.py
------------------------
Reemplaza lectura de /data/professionals.json → PostgreSQL
"""
from __future__ import annotations

from datetime import date, timedelta, datetime
from typing import Dict, Any, List

from agenda import store


FREE_THRESHOLD = 10
LOW_THRESHOLD  = 1
FULL_THRESHOLD = 0


def _load_professionals() -> Dict[str, Any]:
    """Lee profesionales desde PostgreSQL — siempre fresco."""
    from db.supabase_client import get_profesionales
    return get_profesionales()


def _weekday_name(d: date) -> str:
    return d.strftime("%A").lower()


def _day_status(free_slots: int) -> str:
    if free_slots >= FREE_THRESHOLD:
        return "free"
    if free_slots >= LOW_THRESHOLD:
        return "low"
    if free_slots == FULL_THRESHOLD:
        return "full"
    return "empty"


def _count_slots_in_blocks(blocks: List[Dict[str, str]], slot_minutes: int) -> int:
    total = 0
    for b in blocks:
        start   = datetime.strptime(b["start"], "%H:%M")
        end     = datetime.strptime(b["end"],   "%H:%M")
        minutes = int((end - start).total_seconds() / 60)
        total  += minutes // slot_minutes
    return total


def _count_free_slots(
    day_data: Dict[str, Any],
    professional: str,
    current_date: date,
    professionals: Dict[str, Any]
) -> int:
    prof_cfg = professionals.get(professional)
    if not prof_cfg or not prof_cfg.get("active"):
        return -1

    schedule = prof_cfg.get("schedule")
    if not schedule:
        return -1

    weekday    = _weekday_name(current_date)
    day_blocks = schedule.get("days", {}).get(weekday)

    if not day_blocks:
        return -1

    slot_minutes = schedule.get("slotMinutes", 15)
    total_slots  = _count_slots_in_blocks(day_blocks, slot_minutes)

    prof_day = day_data.get(professional, {})
    busy     = len(prof_day.get("slots", {}))

    return max(total_slots - busy, 0)


def range_summary(*, professional: str, start_date: str, days: int) -> Dict[str, Any]:
    professionals = _load_professionals()
    start         = date.fromisoformat(start_date)
    result_days: Dict[str, str] = {}

    for i in range(days):
        current    = start + timedelta(days=i)
        iso        = current.isoformat()
        day_data   = store.read_day(iso)
        free_slots = _count_free_slots(day_data, professional, current, professionals)
        result_days[iso] = "empty" if free_slots == -1 else _day_status(free_slots)

    return {"start_date": start_date, "professional": professional, "days": result_days}


def month_summary(*, professional: str, month: str) -> Dict[str, Any]:
    year, mm   = map(int, month.split("-"))
    start      = date(year, mm, 1)
    next_month = date(year + (mm == 12), (mm % 12) + 1, 1)
    return range_summary(
        professional=professional,
        start_date=start.isoformat(),
        days=(next_month - start).days
    )


def week_summary(*, professional: str, week_start: str) -> Dict[str, Any]:
    return range_summary(professional=professional, start_date=week_start, days=7)
        

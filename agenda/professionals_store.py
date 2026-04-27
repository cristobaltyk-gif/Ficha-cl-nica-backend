"""
agenda/professionals_store.py
Lee/escribe profesionales desde PostgreSQL.
"""
import json
from pathlib import Path
from threading import Lock
from typing import Dict, Any, List

DATA_PATH = Path("/data/professionals.json")
LOCK = Lock()


def _load_all() -> Dict[str, Any]:
    """Lee desde disco como fallback legacy."""
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text("{}", encoding="utf-8")
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_professionals(data: Dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_professionals() -> Dict[str, Any]:
    """Devuelve profesionales activos con schedule desde PostgreSQL."""
    from db.supabase_client import get_profesionales
    return get_profesionales()


def set_day_blocks(
    *,
    professional_id: str,
    weekday: str,
    blocks: List[Dict[str, str]],
    slot_minutes: int = 15
) -> None:
    from db.supabase_client import _get_conn, get_profesionales, save_profesional
    profs = get_profesionales()
    prof  = profs.get(professional_id)
    if not prof:
        raise ValueError("Profesional no existe")
    schedule = prof.get("schedule") or {}
    schedule["slotMinutes"] = slot_minutes
    schedule.setdefault("days", {})[weekday] = blocks
    prof["schedule"] = schedule
    save_profesional(professional_id, prof)


def close_day(*, professional_id: str, weekday: str) -> None:
    from db.supabase_client import get_profesionales, save_profesional
    profs = get_profesionales()
    prof  = profs.get(professional_id)
    if not prof:
        raise ValueError("Profesional no existe")
    days = prof.get("schedule", {}).get("days", {})
    if weekday in days:
        del days[weekday]
    save_profesional(professional_id, prof)


def block_date(*, professional_id: str, date_iso: str) -> None:
    from db.supabase_client import get_profesionales, save_profesional
    profs   = get_profesionales()
    prof    = profs.get(professional_id)
    if not prof:
        raise ValueError("Profesional no existe")
    blocked = prof.get("blocked_dates") or []
    if date_iso not in blocked:
        blocked.append(date_iso)
    prof["blocked_dates"] = blocked
    save_profesional(professional_id, prof)


def unblock_date(*, professional_id: str, date_iso: str) -> None:
    from db.supabase_client import get_profesionales, save_profesional
    profs   = get_profesionales()
    prof    = profs.get(professional_id)
    if not prof:
        raise ValueError("Profesional no existe")
    blocked = prof.get("blocked_dates") or []
    if date_iso in blocked:
        blocked.remove(date_iso)
    prof["blocked_dates"] = blocked
    save_profesional(professional_id, prof)


def list_professionals() -> List[Dict[str, Any]]:
    from db.supabase_client import get_profesionales
    return list(get_profesionales().values())
    

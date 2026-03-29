import json
from pathlib import Path
from threading import Lock
from typing import Dict, Any, List

DATA_PATH = Path("data/professionals.json")
LOCK = Lock()


def load_professionals() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text("{}", encoding="utf-8")
        return {}

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        professionals = json.load(f)

    # 🔒 Regla clínica: sin horario → no hay agenda
    valid = {}
    for pid, p in professionals.items():
        if not p.get("active"):
            continue
        if "schedule" not in p:
            continue
        valid[pid] = p

    return valid


def save_professionals(data: Dict[str, Any]) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_all() -> Dict[str, Any]:
    """Lee todos los profesionales sin filtrar activos/schedule."""
    if not DATA_PATH.exists():
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ======================================================
# MODIFICACIONES
# ======================================================

def set_day_blocks(
    *,
    professional_id: str,
    weekday: str,
    blocks: List[Dict[str, str]],
    slot_minutes: int = 15
) -> None:
    """
    Define bloques para un día — guarda como array directo [{start, end}]
    para ser compatible con AgendaDayController.
    """
    with LOCK:
        data = _load_all()
        prof = data.get(professional_id)
        if not prof:
            raise ValueError("Profesional no existe")

        schedule = prof.setdefault("schedule", {})
        schedule["slotMinutes"] = slot_minutes
        days = schedule.setdefault("days", {})

        # ✅ Array directo — mismo formato que professionals.json
        days[weekday] = blocks

        save_professionals(data)


def close_day(
    *,
    professional_id: str,
    weekday: str
) -> None:
    """Cierra un día completo (no atiende)."""
    with LOCK:
        data = _load_all()
        prof = data.get(professional_id)
        if not prof:
            raise ValueError("Profesional no existe")

        days = prof.get("schedule", {}).get("days", {})
        if weekday in days:
            del days[weekday]

        save_professionals(data)


def block_date(
    *,
    professional_id: str,
    date_iso: str
) -> None:
    """Bloquea una fecha específica (ej: vacaciones)."""
    with LOCK:
        data = _load_all()
        prof = data.get(professional_id)
        if not prof:
            raise ValueError("Profesional no existe")

        blocked = prof.setdefault("blocked_dates", [])
        if date_iso not in blocked:
            blocked.append(date_iso)

        save_professionals(data)


def unblock_date(
    *,
    professional_id: str,
    date_iso: str
) -> None:
    with LOCK:
        data = _load_all()
        prof = data.get(professional_id)
        if not prof:
            raise ValueError("Profesional no existe")

        blocked = prof.get("blocked_dates", [])
        if date_iso in blocked:
            blocked.remove(date_iso)

        save_professionals(data)

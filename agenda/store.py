from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any

# =============================
# Configuración
# =============================
DATA_PATH = Path("data/agenda_future.json")
LOCK = Lock()


# =============================
# Helpers
# =============================
def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_base(store: Dict[str, Any]) -> None:
    store.setdefault("meta", {})
    store.setdefault("calendar", {})
    store.setdefault("index_by_time", {})

    store["meta"].setdefault("version", 1)
    store["meta"]["updated_at"] = _utc_iso()


def _ensure_day_professional(store: Dict[str, Any], date: str, professional: str) -> None:
    store["calendar"].setdefault(date, {})
    store["calendar"][date].setdefault(professional, {
        "schedule": {},
        "slots": {}
    })

    store["index_by_time"].setdefault(date, {})


# =============================
# Lectura / Escritura BASE
# (SIN LOCK)
# =============================
def load_store() -> Dict[str, Any]:
    """
    Lee el JSON completo.
    NO usa lock interno.
    """
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        base = {
            "meta": {
                "version": 1,
                "updated_at": _utc_iso()
            },
            "calendar": {},
            "index_by_time": {}
        }

        DATA_PATH.write_text(
            json.dumps(base, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return base

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_store(store: Dict[str, Any]) -> None:
    """
    Escribe el JSON completo.
    NO usa lock interno.
    """
    _ensure_base(store)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


# =============================
# Lecturas específicas
# =============================
def read_day(date: str) -> Dict[str, Any]:
    store = load_store()
    return store.get("calendar", {}).get(date, {})


def read_occupancy(date: str, time: str) -> Dict[str, str]:
    store = load_store()
    return store.get("index_by_time", {}).get(date, {}).get(time, {})


# =============================
# Mutaciones (CON LOCK)
# =============================
def set_slot(
    *,
    date: str,
    time: str,
    professional: str,
    status: str,
    rut: str | None = None
) -> None:
    """
    Guarda slot en calendar e index_by_time.
    """
    with LOCK:
        store = load_store()
        _ensure_base(store)
        _ensure_day_professional(store, date, professional)

        slot = {"status": status}
        if rut:
            slot["rut"] = rut

        store["calendar"][date][professional]["slots"][time] = slot

        store["index_by_time"][date].setdefault(time, {})
        store["index_by_time"][date][time][professional] = status

        save_store(store)


def clear_slot(
    *,
    date: str,
    time: str,
    professional: str
) -> None:
    """
    Elimina slot (available implícito).
    """
    with LOCK:
        store = load_store()
        _ensure_base(store)

        # calendar
        day = store.get("calendar", {}).get(date, {})
        prof = day.get(professional, {})
        slots = prof.get("slots", {})

        if time in slots:
            del slots[time]

        # index_by_time
        idx_day = store.get("index_by_time", {}).get(date, {})
        if time in idx_day and professional in idx_day[time]:
            del idx_day[time][professional]
            if not idx_day[time]:
                del idx_day[time]

        save_store(store)


def cleanup_past(*, keep_from_date: str) -> None:
    """
    Borra días anteriores a keep_from_date.
    """
    with LOCK:
        store = load_store()
        _ensure_base(store)

        for d in list(store.get("calendar", {}).keys()):
            if d < keep_from_date:
                del store["calendar"][d]

        for d in list(store.get("index_by_time", {}).keys()):
            if d < keep_from_date:
                del store["index_by_time"][d]

        save_store(store)

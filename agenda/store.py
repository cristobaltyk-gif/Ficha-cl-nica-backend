"""
agenda/store.py
---------------
Reemplaza /data/agenda_future.json → PostgreSQL
Misma interfaz que el store original.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from db.supabase_client import _get_conn


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ══════════════════════════════════════════════════════════════
# LECTURA
# ══════════════════════════════════════════════════════════════

def read_day(date: str) -> Dict[str, Any]:
    """
    Retorna estructura compatible con el frontend:
    {
        professional_id: {
            "slots": {
                "HH:MM": {"status": ..., "rut": ..., ...}
            }
        }
    }
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT professional, time, status, rut, extra
                FROM slots
                WHERE date = %s
            """, (date,))
            rows = cur.fetchall()

    result: Dict[str, Any] = {}
    for row in rows:
        prof = row["professional"]
        if prof not in result:
            result[prof] = {"slots": {}}
        slot = {"status": row["status"]}
        if row["rut"]:
            slot["rut"] = row["rut"]
        if row["extra"]:
            slot.update(row["extra"])
        result[prof]["slots"][row["time"]] = slot

    return result


def read_occupancy(date: str, time: str) -> Dict[str, str]:
    """
    Retorna {professional_id: status} para un slot específico.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT professional, status
                FROM slots
                WHERE date = %s AND time = %s
            """, (date, time))
            rows = cur.fetchall()

    return {row["professional"]: row["status"] for row in rows}


# ══════════════════════════════════════════════════════════════
# ESCRITURA
# ══════════════════════════════════════════════════════════════

def set_slot(
    *,
    date: str,
    time: str,
    professional: str,
    status: str,
    rut: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Crea o actualiza un slot.
    PostgreSQL maneja la concurrencia — ON CONFLICT actualiza atómicamente.
    """
    import json
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO slots (date, time, professional, status, rut, extra, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, time, professional)
                DO UPDATE SET
                    status     = EXCLUDED.status,
                    rut        = EXCLUDED.rut,
                    extra      = EXCLUDED.extra,
                    updated_at = EXCLUDED.updated_at
            """, (
                date, time, professional, status, rut,
                json.dumps(extra or {}),
                _utc_iso()
            ))
            conn.commit()


def clear_slot(
    *,
    date: str,
    time: str,
    professional: str,
) -> None:
    """Elimina un slot (queda implícitamente disponible)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM slots
                WHERE date = %s AND time = %s AND professional = %s
            """, (date, time, professional))
            conn.commit()


def cleanup_past(*, keep_from_date: str) -> None:
    """Elimina slots anteriores a keep_from_date."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM slots WHERE date < %s
            """, (keep_from_date,))
            conn.commit()


# ══════════════════════════════════════════════════════════════
# COMPATIBILIDAD — load_store / save_store
# Mantiene interfaz legacy para control_gratuito y sobrecupo
# ══════════════════════════════════════════════════════════════

def load_store() -> dict:
    """
    Retorna estructura compatible con el código legacy:
    {
        "calendar": {
            "YYYY-MM-DD": {
                "professional_id": {
                    "slots": {
                        "HH:MM": {"status": ..., "rut": ..., ...extra}
                    }
                }
            }
        },
        "index_by_time": {}
    }
    """
    import json as _json
    from db.supabase_client import _get_conn

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT date, time, professional, status, rut, extra FROM slots")
            rows = cur.fetchall()

    calendar = {}
    for row in rows:
        date = row["date"]
        prof = row["professional"]
        time = row["time"]

        calendar.setdefault(date, {})
        calendar[date].setdefault(prof, {"schedule": {}, "slots": {}})

        slot = {"status": row["status"]}
        if row["rut"]:
            slot["rut"] = row["rut"]
        if row["extra"]:
            extra = row["extra"] if isinstance(row["extra"], dict) else _json.loads(row["extra"])
            slot.update(extra)

        calendar[date][prof]["slots"][time] = slot

    return {
        "meta":          {"version": 1},
        "calendar":      calendar,
        "index_by_time": {}
    }


def save_store(store: dict) -> None:
    """
    Persiste todos los slots del store a PostgreSQL.
    Reemplaza completamente los slots de las fechas presentes.
    """
    import json as _json
    from db.supabase_client import _get_conn

    calendar = store.get("calendar", {})

    with _get_conn() as conn:
        with conn.cursor() as cur:
            for date, day_data in calendar.items():
                for prof, prof_data in day_data.items():
                    for time, slot in prof_data.get("slots", {}).items():
                        status = slot.get("status", "reserved")
                        rut    = slot.get("rut")
                        extra  = {k: v for k, v in slot.items() if k not in ("status", "rut")}
                        cur.execute("""
                            INSERT INTO slots (date, time, professional, status, rut, extra, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (date, time, professional) DO UPDATE SET
                                status     = EXCLUDED.status,
                                rut        = EXCLUDED.rut,
                                extra      = EXCLUDED.extra,
                                updated_at = EXCLUDED.updated_at
                        """, (date, time, prof, status, rut, _json.dumps(extra)))
            conn.commit()

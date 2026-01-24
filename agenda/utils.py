from __future__ import annotations

from datetime import datetime, date, time, timezone
from typing import Tuple


# -----------------------------
# Tiempo "oficial" backend
# -----------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_utc() -> date:
    return now_utc().date()


# -----------------------------
# Parsers estrictos
# -----------------------------
def parse_yyyy_mm_dd(d: str) -> date:
    # espera "YYYY-MM-DD"
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("date inválida (formato esperado YYYY-MM-DD)")


def parse_hh_mm(t: str) -> time:
    # espera "HH:MM" 24h
    try:
        return datetime.strptime(t, "%H:%M").time()
    except Exception:
        raise ValueError("time inválida (formato esperado HH:MM)")


def to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def is_on_interval(hhmm: str, interval: int) -> bool:
    tm = parse_hh_mm(hhmm)
    return (to_minutes(tm) % interval) == 0


# -----------------------------
# Reglas temporales de agenda
# Agenda = SOLO futuro (y hoy hacia adelante)
# -----------------------------
def is_future_slot(slot_date: str, slot_time: str) -> bool:
    d = parse_yyyy_mm_dd(slot_date)
    t = parse_hh_mm(slot_time)

    now = now_utc()
    # Comparamos usando UTC (simple y consistente)
    slot_dt = datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=timezone.utc)
    return slot_dt >= now


def assert_future_slot(slot_date: str, slot_time: str) -> None:
    if not is_future_slot(slot_date, slot_time):
        raise ValueError("No se permiten slots en el pasado (agenda es solo futuro).")


# -----------------------------
# Normalización RUT (mínima)
# NO valida dígito verificador aquí (eso puede ir en ficha clínica)
# -----------------------------
def normalize_rut(rut: str) -> str:
    r = rut.strip().upper().replace(" ", "")
    # mantener puntos y guión tal cual si vienen; solo limpieza mínima
    return r


# -----------------------------
# Helpers para rangos de horario
# -----------------------------
def build_time_range(start_hhmm: str, end_hhmm: str, interval: int) -> list[str]:
    """
    Genera lista de HH:MM desde start inclusive hasta end exclusiva,
    avanzando en interval minutos.
    """
    if interval <= 0:
        raise ValueError("interval debe ser > 0")

    st = parse_hh_mm(start_hhmm)
    et = parse_hh_mm(end_hhmm)

    start_m = to_minutes(st)
    end_m = to_minutes(et)

    if end_m <= start_m:
        raise ValueError("end debe ser mayor que start")

    out = []
    cur = start_m
    while cur < end_m:
        hh = str(cur // 60).zfill(2)
        mm = str(cur % 60).zfill(2)
        out.append(f"{hh}:{mm}")
        cur += interval
    return out

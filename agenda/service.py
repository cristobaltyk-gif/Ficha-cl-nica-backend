from __future__ import annotations

from typing import Dict, Any
from datetime import timedelta

from agenda import store
from agenda.models import (
    CreateSlotRequest,
    CancelSlotRequest,
    RescheduleRequest,
    MutationResult,
    SlotStatus,
)
from agenda.utils import (
    assert_future_slot,
    normalize_rut,
    parse_yyyy_mm_dd,
    parse_hh_mm,
    is_on_interval,
    today_utc,
)


# =============================
# Configuración operativa
# =============================
DEFAULT_INTERVAL_MIN = 15  # agenda médica estándar
AUTO_CLEANUP_DAYS_AHEAD = 0  # limpiar todo < hoy (solo futuro)


# =============================
# Lecturas de negocio
# =============================
def get_day(date: str) -> Dict[str, Any]:
    # valida formato fecha
    parse_yyyy_mm_dd(date)
    return store.read_day(date)


def get_occupancy(date: str, time: str) -> Dict[str, SlotStatus]:
    # valida formato
    parse_yyyy_mm_dd(date)
    parse_hh_mm(time)
    return store.read_occupancy(date, time)


# =============================
# Reglas internas
# =============================
def _assert_interval(time: str, interval: int = DEFAULT_INTERVAL_MIN) -> None:
    if not is_on_interval(time, interval):
        raise ValueError(f"La hora debe caer en intervalos de {interval} minutos.")


def _assert_free(date: str, time: str, professional: str) -> None:
    occ = get_occupancy(date, time)
    if occ.get(professional) not in (None, "available"):
        raise ValueError("El slot ya está ocupado.")


# =============================
# Mutaciones
# =============================
def create_slot(req: CreateSlotRequest) -> MutationResult:
    # validaciones
    parse_yyyy_mm_dd(req.date)
    parse_hh_mm(req.time)
    _assert_interval(req.time)
    assert_future_slot(req.date, req.time)

    professional = req.professional
    rut = normalize_rut(req.rut)

    # leer ocupación antes de mutar
    _assert_free(req.date, req.time, professional)

    # escribir
    store.set_slot(
        date=req.date,
        time=req.time,
        professional=professional,
        status=req.status,
        rut=rut,
    )

    return MutationResult(
        ok=True,
        message="Slot creado",
        date=req.date,
        professional=professional,
        slot={"time": req.time, "status": req.status, "rut": rut},
    )


def cancel_slot(req: CancelSlotRequest) -> MutationResult:
    # validaciones
    parse_yyyy_mm_dd(req.date)
    parse_hh_mm(req.time)
    assert_future_slot(req.date, req.time)

    professional = req.professional

    # limpiar slot (vuelve implícitamente a available)
    store.clear_slot(
        date=req.date,
        time=req.time,
        professional=professional,
    )

    return MutationResult(
        ok=True,
        message="Slot anulado",
        date=req.date,
        professional=professional,
        slot={"time": req.time, "status": "available"},
    )


def reschedule(req: RescheduleRequest) -> MutationResult:
    # from
    f = req.from_slot
    t = req.to_slot

    parse_yyyy_mm_dd(f.date)
    parse_hh_mm(f.time)
    parse_yyyy_mm_dd(t.date)
    parse_hh_mm(t.time)

    _assert_interval(f.time)
    _assert_interval(t.time)

    # ambos deben ser futuro
    assert_future_slot(f.date, f.time)
    assert_future_slot(t.date, t.time)

    professional = f.professional

    # leer ocupación destino
    _assert_free(t.date, t.time, professional)

    # leer slot origen (si no existe, error)
    day = store.read_day(f.date)
    prof = day.get(professional, {})
    slot = prof.get("slots", {}).get(f.time)
    if not slot or slot.get("status") not in ("reserved", "confirmed"):
        raise ValueError("No existe un slot válido para reprogramar.")

    rut = slot.get("rut")

    # transacción lógica:
    # 1) crear nuevo
    store.set_slot(
        date=t.date,
        time=t.time,
        professional=professional,
        status=slot["status"],
        rut=rut,
    )

    # 2) limpiar antiguo
    store.clear_slot(
        date=f.date,
        time=f.time,
        professional=professional,
    )

    return MutationResult(
        ok=True,
        message="Slot reprogramado",
        date=t.date,
        professional=professional,
        slot={"time": t.time, "status": slot["status"], "rut": rut},
        moved_from={"date": f.date, "time": f.time},
        moved_to={"date": t.date, "time": t.time},
    )


# =============================
# Limpieza diaria (pasado)
# =============================
def daily_cleanup() -> None:
    """
    Elimina todo lo anterior a hoy.
    Llamar 1 vez al día (cron) o al primer request del día.
    """
    keep_from = today_utc().isoformat()
    store.cleanup_past(keep_from_date=keep_from)

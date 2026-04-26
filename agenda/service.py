"""
agenda/service.py
-----------------
Reemplaza lecturas de /data/professionals.json y /data/pacientes → PostgreSQL
Misma interfaz que el service original.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Dict, Any

from agenda import store
from agenda.models import (
    CreateSlotRequest,
    ConfirmSlotRequest,
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

DEFAULT_INTERVAL_MIN = 15


# ══════════════════════════════════════════════════════════════
# HELPERS — ahora leen desde PostgreSQL
# ══════════════════════════════════════════════════════════════

def _load_admin(rut: str) -> dict | None:
    from db.supabase_client import get_paciente
    return get_paciente(rut)


def _get_professional_name(professional_id: str) -> str:
    from db.supabase_client import get_profesionales
    profs = get_profesionales()
    return profs.get(professional_id, {}).get("name", professional_id)


def _calcular_edad(fecha_nacimiento: str) -> int | None:
    if not fecha_nacimiento:
        return None
    try:
        partes = str(fecha_nacimiento).strip().replace("/", "-").split("-")
        if len(partes) == 3:
            if len(partes[0]) == 4:
                anio, mes, dia = int(partes[0]), int(partes[1]), int(partes[2])
            else:
                dia, mes, anio = int(partes[0]), int(partes[1]), int(partes[2])
            hoy = _date.today()
            edad = hoy.year - anio
            if (hoy.month, hoy.day) < (mes, dia):
                edad -= 1
            return edad if edad > 0 else None
    except Exception:
        return None


def _enviar_confirmacion_reserva(rut, date, time, professional) -> None:
    try:
        from notifications.email_service import enviar_confirmacion_reserva
        admin = _load_admin(rut)
        if not admin:
            return
        email = admin.get("email", "").strip()
        if not email:
            return
        nombre     = f"{admin.get('nombre', '')} {admin.get('apellido_paterno', '')}".strip()
        nombre_prof = _get_professional_name(professional)
        edad       = _calcular_edad(admin.get("fecha_nacimiento", ""))
        sexo       = admin.get("sexo", "")
        enviar_confirmacion_reserva(
            email_paciente=email,
            nombre_paciente=nombre,
            rut_paciente=rut,
            fecha=date,
            hora=time,
            profesional_nombre=nombre_prof,
            edad_paciente=edad,
            sexo_paciente=sexo,
        )
    except Exception as e:
        print(f"⚠️ No se pudo enviar email de confirmación: {e}")


# ══════════════════════════════════════════════════════════════
# LECTURAS
# ══════════════════════════════════════════════════════════════

def get_day(date: str) -> Dict[str, Any]:
    parse_yyyy_mm_dd(date)
    return store.read_day(date)


def get_occupancy(date: str, time: str) -> Dict[str, SlotStatus]:
    parse_yyyy_mm_dd(date)
    parse_hh_mm(time)
    return store.read_occupancy(date, time)


# ══════════════════════════════════════════════════════════════
# REGLAS
# ══════════════════════════════════════════════════════════════

def _assert_interval(time: str, interval: int = DEFAULT_INTERVAL_MIN) -> None:
    if not is_on_interval(time, interval):
        raise ValueError(f"La hora debe caer en intervalos de {interval} minutos.")


def _assert_free(date: str, time: str, professional: str) -> None:
    occ = get_occupancy(date, time)
    if occ.get(professional) not in (None, "available"):
        raise ValueError("El slot ya está ocupado.")


def _assert_not_past_date(slot_date: str) -> None:
    if parse_yyyy_mm_dd(slot_date) < today_utc():
        raise ValueError("No se puede cancelar un slot de una fecha pasada.")


# ══════════════════════════════════════════════════════════════
# MUTACIONES
# ══════════════════════════════════════════════════════════════

def create_slot(req: CreateSlotRequest) -> MutationResult:
    parse_yyyy_mm_dd(req.date)
    parse_hh_mm(req.time)
    _assert_interval(req.time)
    assert_future_slot(req.date, req.time)

    professional = req.professional
    rut = normalize_rut(req.rut)

    _assert_free(req.date, req.time, professional)

    store.set_slot(
        date=req.date,
        time=req.time,
        professional=professional,
        status=req.status,
        rut=rut,
    )

    _enviar_confirmacion_reserva(rut, req.date, req.time, professional)

    return MutationResult(
        ok=True,
        message="Slot creado",
        date=req.date,
        professional=professional,
        slot={"time": req.time, "status": req.status, "rut": rut},
    )


def confirm_slot(req: ConfirmSlotRequest) -> MutationResult:
    parse_yyyy_mm_dd(req.date)
    parse_hh_mm(req.time)

    professional = req.professional
    day  = store.read_day(req.date)
    prof = day.get(professional, {})
    slot = prof.get("slots", {}).get(req.time)

    if not slot:
        raise ValueError("El slot no existe.")
    if slot.get("status") != "reserved":
        raise ValueError("Solo se pueden confirmar slots reservados.")

    rut = slot.get("rut")

    store.set_slot(
        date=req.date,
        time=req.time,
        professional=professional,
        status="confirmed",
        rut=rut,
    )

    return MutationResult(
        ok=True,
        message="Slot confirmado",
        date=req.date,
        professional=professional,
        slot={"time": req.time, "status": "confirmed", "rut": rut},
    )


def cancel_slot(req: CancelSlotRequest) -> MutationResult:
    parse_yyyy_mm_dd(req.date)
    parse_hh_mm(req.time)
    _assert_not_past_date(req.date)

    store.clear_slot(
        date=req.date,
        time=req.time,
        professional=req.professional,
    )

    return MutationResult(
        ok=True,
        message="Slot anulado",
        date=req.date,
        professional=req.professional,
        slot={"time": req.time, "status": "available"},
    )


def reschedule(req: RescheduleRequest) -> MutationResult:
    f = req.from_slot
    t = req.to_slot

    parse_yyyy_mm_dd(f.date)
    parse_hh_mm(f.time)
    parse_yyyy_mm_dd(t.date)
    parse_hh_mm(t.time)

    _assert_interval(f.time)
    _assert_interval(t.time)
    assert_future_slot(f.date, f.time)
    assert_future_slot(t.date, t.time)

    professional = f.professional
    _assert_free(t.date, t.time, professional)

    day  = store.read_day(f.date)
    prof = day.get(professional, {})
    slot = prof.get("slots", {}).get(f.time)

    if not slot or slot.get("status") not in ("reserved", "confirmed"):
        raise ValueError("No existe un slot válido para reprogramar.")

    rut = slot.get("rut")

    store.set_slot(
        date=t.date, time=t.time,
        professional=professional,
        status=slot["status"], rut=rut,
    )
    store.clear_slot(
        date=f.date, time=f.time,
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


def daily_cleanup() -> None:
    keep_from = today_utc().isoformat()
    store.cleanup_past(keep_from_date=keep_from)
    

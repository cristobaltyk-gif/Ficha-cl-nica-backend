"""
agenda/bloqueo_router.py
------------------------
Endpoints para bloquear días o slots de agenda.
Notifica automáticamente a pacientes con hora reservada.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth
from agenda.store import read_day, set_slot, clear_slot
from db.supabase_client import get_paciente, get_profesionales

router = APIRouter(prefix="/agenda", tags=["agenda"])


class BloquearDiaRequest(BaseModel):
    date:         str
    professional: str
    motivo:       Optional[str] = "El profesional no estará disponible este día"


class BloquearSlotRequest(BaseModel):
    date:         str
    time:         str
    professional: str


def _can_manage(user: dict, professional: str) -> bool:
    role = user.get("role", {}).get("name", "")
    if role in ("secretaria", "admin"):
        return True
    if role == "medico":
        return user.get("professional") == professional
    return False


def _get_professional_name(professional: str) -> str:
    profs = get_profesionales()
    return profs.get(professional, {}).get("name", professional)


@router.post("/bloquear-dia")
def bloquear_dia(data: BloquearDiaRequest, user=Depends(require_internal_auth)):
    """
    Bloquea todos los slots disponibles del día y notifica
    a pacientes con hora reservada.
    """
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado")

    from notifications.email_service import enviar_notificacion_bloqueo

    day_data     = read_day(data.date)
    prof_slots   = day_data.get(data.professional, {}).get("slots", {})
    nombre_prof  = _get_professional_name(data.professional)

    notificados  = 0
    eliminados   = 0
    errores      = []

    for time, slot in prof_slots.items():
        status = slot.get("status", "")

        # Notificar pacientes con hora reservada
        if status in ("reserved", "confirmed"):
            rut = slot.get("rut")
            if rut:
                try:
                    admin = get_paciente(rut)
                    email = admin.get("email", "").strip() if admin else ""
                    if email:
                        nombre = f"{admin.get('nombre','')} {admin.get('apellido_paterno','')}".strip()
                        enviar_notificacion_bloqueo(
                            email_paciente=email,
                            nombre_paciente=nombre,
                            fecha=data.date,
                            hora=time,
                            profesional_nombre=nombre_prof,
                            motivo=data.motivo,
                        )
                        notificados += 1
                except Exception as e:
                    errores.append(f"notificar {rut} {time}: {e}")

        # Eliminar slot (liberar o bloquear)
        try:
            clear_slot(date=data.date, time=time, professional=data.professional)
            eliminados += 1
        except Exception as e:
            errores.append(f"eliminar {time}: {e}")

    return {
        "ok":          True,
        "date":        data.date,
        "professional": data.professional,
        "eliminados":  eliminados,
        "notificados": notificados,
        "errores":     errores,
    }


@router.post("/bloquear-slot")
def bloquear_slot(data: BloquearSlotRequest, user=Depends(require_internal_auth)):
    """Bloquea un slot específico."""
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado")

    set_slot(
        date=data.date, time=data.time,
        professional=data.professional,
        status="blocked"
    )
    return {"ok": True}


@router.post("/desbloquear-slot")
def desbloquear_slot(data: BloquearSlotRequest, user=Depends(require_internal_auth)):
    """Desbloquea un slot específico."""
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado")

    clear_slot(date=data.date, time=data.time, professional=data.professional)
    return {"ok": True}
  

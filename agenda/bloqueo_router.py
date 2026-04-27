"""
agenda/bloqueo_router.py
------------------------
Bloqueo de fechas específicas en agenda.
- Secretaria: puede bloquear cualquier profesional
- Médico/Kine: solo puede bloquear su propio horario
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth
from agenda.store import read_day, clear_slot
from db.supabase_client import get_paciente, get_profesionales

router = APIRouter(prefix="/agenda", tags=["agenda"])


class BloquearDiaRequest(BaseModel):
    date:         str
    professional: str
    motivo:       Optional[str] = "El profesional no estará disponible este día"


def _can_manage(user: dict, professional: str) -> bool:
    role = user.get("role", {}).get("name", "")
    if role in ("secretaria", "admin"):
        return True
    if role in ("medico", "kine"):
        return user.get("professional") == professional
    return False


def _get_professional_name(professional: str) -> str:
    profs = get_profesionales()
    return profs.get(professional, {}).get("name", professional)


@router.post("/bloquear-dia")
def bloquear_dia(data: BloquearDiaRequest, user=Depends(require_internal_auth)):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado para bloquear este profesional")

    from notifications.email_service import enviar_notificacion_bloqueo
    from agenda import professionals_store as prof_store

    day_data    = read_day(data.date)
    prof_slots  = day_data.get(data.professional, {}).get("slots", {})
    nombre_prof = _get_professional_name(data.professional)

    notificados = 0
    errores     = []

    # 1. Notificar y eliminar slots reservados
    for time, slot in prof_slots.items():
        if slot.get("status") in ("reserved", "confirmed"):
            rut = slot.get("rut")
            if rut:
                try:
                    admin = get_paciente(rut)
                    email = (admin.get("email") or "").strip() if admin else ""
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

        # Eliminar el slot
        try:
            clear_slot(date=data.date, time=time, professional=data.professional)
        except Exception as e:
            errores.append(f"eliminar {time}: {e}")

    # 2. Agregar fecha a blocked_dates del profesional
    try:
        prof_store.block_date(professional_id=data.professional, date_iso=data.date)
    except Exception as e:
        errores.append(f"block_date: {e}")

    return {
        "ok":           True,
        "date":         data.date,
        "professional": data.professional,
        "notificados":  notificados,
        "errores":      errores,
    }


@router.delete("/bloquear-dia/{professional}/{date}")
def desbloquear_dia(professional: str, date: str, user=Depends(require_internal_auth)):
    if not _can_manage(user, professional):
        raise HTTPException(status_code=403, detail="No autorizado para desbloquear este profesional")

    from agenda import professionals_store as prof_store
    try:
        prof_store.unblock_date(professional_id=professional, date_iso=date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "date": date, "professional": professional}


class BloquearSlotRequest(BaseModel):
    date:         str
    time:         str
    professional: str


@router.post("/bloquear-slot")
def bloquear_slot(data: BloquearSlotRequest, user=Depends(require_internal_auth)):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado")
    from agenda.store import set_slot
    set_slot(date=data.date, time=data.time, professional=data.professional, status="blocked")
    return {"ok": True}


@router.post("/desbloquear-slot")
def desbloquear_slot(data: BloquearSlotRequest, user=Depends(require_internal_auth)):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="No autorizado")
    from agenda.store import clear_slot
    clear_slot(date=data.date, time=data.time, professional=data.professional)
    return {"ok": True}
                      

"""
modules/control/control_gratuito_router.py

Endpoints para el flujo de control gratuito:
1. POST /api/control/gratuito     — secretaria marca slot como gratuito + envía email
2. GET  /api/control/confirmar    — paciente confirma via link
3. POST /api/control/aceptar      — médico acepta el control gratuito
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.internal_auth import require_internal_auth
from agenda.store import load_store, save_store
from notifications.email_service import enviar_confirmacion_gratuito

router = APIRouter(prefix="/api/control", tags=["Control Gratuito"])

# Archivo donde guardamos los tokens pendientes
TOKENS_PATH = Path("/data/control_tokens.json")
LOCK        = Lock()

BASE_PACIENTES = Path("/data/pacientes")


# ======================================================
# HELPERS
# ======================================================

def _load_tokens() -> dict:
    if not TOKENS_PATH.exists():
        return {}
    with open(TOKENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tokens(data: dict) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_slot(store: dict, date: str, professional: str, time: str) -> dict:
    return (
        store.get("calendar", {})
             .get(date, {})
             .get(professional, {})
             .get("slots", {})
             .get(time, {})
    )


def _set_slot_field(store: dict, date: str, professional: str, time: str, updates: dict) -> None:
    slot = (
        store["calendar"]
             .setdefault(date, {})
             .setdefault(professional, {"schedule": {}, "slots": {}})
             ["slots"]
             .setdefault(time, {})
    )
    slot.update(updates)


def _load_admin(rut: str) -> dict | None:
    f = BASE_PACIENTES / rut / "admin.json"
    if not f.exists():
        return None
    with open(f, "r", encoding="utf-8") as fp:
        return json.load(fp)


# ======================================================
# SCHEMAS
# ======================================================

class MarcarGratuitoRequest(BaseModel):
    date:         str
    time:         str
    professional: str


class AceptarGratuitoRequest(BaseModel):
    date:         str
    time:         str
    professional: str


# ======================================================
# 1. SECRETARIA — marca slot como gratuito + envía email
# ======================================================

@router.post("/gratuito")
def marcar_gratuito(
    data: MarcarGratuitoRequest,
    user=Depends(require_internal_auth)
):
    with LOCK:
        store = load_store()

        slot = _get_slot(store, data.date, data.professional, data.time)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")

        if slot.get("status") not in ("reserved", "confirmed"):
            raise HTTPException(status_code=400, detail="El slot no tiene reserva activa")

        rut = slot.get("rut")
        if not rut:
            raise HTTPException(status_code=400, detail="Slot sin RUT de paciente")

        # Cargar datos del paciente
        admin = _load_admin(rut)
        if not admin:
            raise HTTPException(status_code=404, detail="Ficha del paciente no encontrada")

        email = admin.get("email", "").strip()
        if not email:
            raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

        # Generar token único
        token = secrets.token_urlsafe(32)

        # Guardar en slot
        _set_slot_field(store, data.date, data.professional, data.time, {
            "gratuito":            True,
            "gratuito_token":      token,
            "gratuito_confirmado": False,
            "gratuito_aceptado":   False,
            "gratuito_marcado_por": user["usuario"],
        })
        save_store(store)

        # Guardar token → referencia al slot
        tokens = _load_tokens()
        tokens[token] = {
            "date":         data.date,
            "time":         data.time,
            "professional": data.professional,
            "rut":          rut,
            "created_at":   datetime.now(timezone.utc).isoformat()
        }
        _save_tokens(tokens)

    # Enviar email al paciente
    nombre = f"{admin.get('nombre', '')} {admin.get('apellido_paterno', '')}".strip()

    ok = enviar_confirmacion_gratuito(
        email_paciente=email,
        nombre_paciente=nombre,
        fecha=data.date,
        hora=data.time,
        profesional=data.professional,
        token=token
    )

    return {
        "ok":           True,
        "email_enviado": ok,
        "email":        email
    }


# ======================================================
# 2. PACIENTE — confirma via link (sin auth)
# ======================================================

@router.get("/confirmar")
def confirmar_gratuito(token: str):
    with LOCK:
        tokens = _load_tokens()
        ref    = tokens.get(token)

        if not ref:
            raise HTTPException(status_code=404, detail="Token inválido o expirado")

        store = load_store()

        slot = _get_slot(store, ref["date"], ref["professional"], ref["time"])
        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")

        if slot.get("gratuito_confirmado"):
            return {"ok": True, "mensaje": "Ya confirmado anteriormente"}

        _set_slot_field(store, ref["date"], ref["professional"], ref["time"], {
            "gratuito_confirmado": True,
        })
        save_store(store)

        # Eliminar token usado
        del tokens[token]
        _save_tokens(tokens)

    return {
        "ok":      True,
        "mensaje": "¡Gracias! Su atención gratuita ha sido confirmada. El médico será notificado."
    }


# ======================================================
# 3. MÉDICO — acepta el control gratuito
# ======================================================

@router.post("/aceptar")
def aceptar_gratuito(
    data: AceptarGratuitoRequest,
    user=Depends(require_internal_auth)
):
    with LOCK:
        store = load_store()

        slot = _get_slot(store, data.date, data.professional, data.time)
        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")

        if not slot.get("gratuito"):
            raise HTTPException(status_code=400, detail="Este slot no está marcado como gratuito")

        if not slot.get("gratuito_confirmado"):
            raise HTTPException(status_code=400, detail="El paciente aún no ha confirmado")

        _set_slot_field(store, data.date, data.professional, data.time, {
            "gratuito_aceptado":    True,
            "gratuito_aceptado_por": user["usuario"],
        })
        save_store(store)

    return {"ok": True}
  

"""
modules/control/control_gratuito_router.py
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from auth.internal_auth import require_internal_auth
from agenda.store import load_store, save_store
from notifications.email_service import enviar_confirmacion_gratuito

router = APIRouter(prefix="/api/control", tags=["Control Gratuito"])

TOKENS_PATH       = Path("/data/control_tokens.json")
PROFESSIONALS_PATH = Path("/data/professionals.json")
LOCK              = Lock()
BASE_PACIENTES    = Path("/data/pacientes")


def _load_tokens() -> dict:
    if not TOKENS_PATH.exists():
        return {}
    with open(TOKENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tokens(data: dict) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_professional_name(professional_id: str) -> str:
    if not PROFESSIONALS_PATH.exists():
        return professional_id
    with open(PROFESSIONALS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(professional_id, {}).get("name", professional_id)


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


class MarcarGratuitoRequest(BaseModel):
    date:         str
    time:         str
    professional: str


class AceptarGratuitoRequest(BaseModel):
    date:         str
    time:         str
    professional: str


# ======================================================
# 1. SECRETARIA — marca slot + envía email
# ======================================================

@router.post("/gratuito")
def marcar_gratuito(
    data: MarcarGratuitoRequest,
    user=Depends(require_internal_auth)
):
    with LOCK:
        store = load_store()
        slot  = _get_slot(store, data.date, data.professional, data.time)

        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")
        if slot.get("status") not in ("reserved", "confirmed"):
            raise HTTPException(status_code=400, detail="El slot no tiene reserva activa")

        rut = slot.get("rut")
        if not rut:
            raise HTTPException(status_code=400, detail="Slot sin RUT de paciente")

        admin = _load_admin(rut)
        if not admin:
            raise HTTPException(status_code=404, detail="Ficha del paciente no encontrada")

        email = admin.get("email", "").strip()
        if not email:
            raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

        token = secrets.token_urlsafe(32)

        _set_slot_field(store, data.date, data.professional, data.time, {
            "gratuito":             True,
            "gratuito_token":       token,
            "gratuito_confirmado":  False,
            "gratuito_aceptado":    False,
            "gratuito_marcado_por": user["usuario"],
        })
        save_store(store)

        tokens = _load_tokens()
        tokens[token] = {
            "date":         data.date,
            "time":         data.time,
            "professional": data.professional,
            "rut":          rut,
            "created_at":   datetime.now(timezone.utc).isoformat()
        }
        _save_tokens(tokens)

    nombre_paciente    = f"{admin.get('nombre', '')} {admin.get('apellido_paterno', '')}".strip()
    nombre_profesional = _get_professional_name(data.professional)

    ok = enviar_confirmacion_gratuito(
        email_paciente=email,
        nombre_paciente=nombre_paciente,
        fecha=data.date,
        hora=data.time,
        profesional_nombre=nombre_profesional,
        token=token
    )

    return {"ok": True, "email_enviado": ok, "email": email}


# ======================================================
# 2. PACIENTE — confirma via link → responde HTML
# ======================================================

@router.get("/confirmar", response_class=HTMLResponse)
def confirmar_gratuito(token: str):
    with LOCK:
        tokens = _load_tokens()
        ref    = tokens.get(token)

        if not ref:
            return HTMLResponse(content=_html_page(
                titulo="Enlace inválido",
                mensaje="Este enlace ya fue usado o ha expirado.",
                color="#ef4444", icono="❌"
            ), status_code=404)

        store = load_store()
        slot  = _get_slot(store, ref["date"], ref["professional"], ref["time"])

        if not slot:
            return HTMLResponse(content=_html_page(
                titulo="Cita no encontrada",
                mensaje="No se encontró la cita asociada a este enlace.",
                color="#ef4444", icono="❌"
            ), status_code=404)

        if slot.get("gratuito_confirmado"):
            return HTMLResponse(content=_html_page(
                titulo="Ya confirmado",
                mensaje="Su atención gratuita ya fue confirmada anteriormente. ¡Gracias!",
                color="#16a34a", icono="✅"
            ))

        _set_slot_field(store, ref["date"], ref["professional"], ref["time"], {
            "gratuito_confirmado": True,
        })
        save_store(store)

        del tokens[token]
        _save_tokens(tokens)

    return HTMLResponse(content=_html_page(
        titulo="¡Confirmado!",
        mensaje=f"Su atención del {ref['date']} a las {ref['time']} ha sido confirmada como gratuita. El médico ha sido notificado.",
        color="#16a34a", icono="✅"
    ))


# ======================================================
# 3. MÉDICO — acepta
# ======================================================

@router.post("/aceptar")
def aceptar_gratuito(
    data: AceptarGratuitoRequest,
    user=Depends(require_internal_auth)
):
    with LOCK:
        store = load_store()
        slot  = _get_slot(store, data.date, data.professional, data.time)

        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")
        if not slot.get("gratuito"):
            raise HTTPException(status_code=400, detail="Este slot no está marcado como gratuito")
        if not slot.get("gratuito_confirmado"):
            raise HTTPException(status_code=400, detail="El paciente aún no ha confirmado")

        _set_slot_field(store, data.date, data.professional, data.time, {
            "gratuito_aceptado":     True,
            "gratuito_aceptado_por": user["usuario"],
        })
        save_store(store)

    return {"ok": True}


# ======================================================
# HTML helper
# ======================================================

def _html_page(titulo: str, mensaje: str, color: str, icono: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Instituto de Cirugía Articular</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Helvetica Neue', Arial, sans-serif;
      background: #f8fafc;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .card {{
      background: #fff;
      border-radius: 16px;
      padding: 40px 32px;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    .logo {{ height: 50px; margin-bottom: 24px; }}
    .icono {{ font-size: 52px; margin-bottom: 20px; }}
    .titulo {{ font-size: 22px; font-weight: 700; color: {color}; margin-bottom: 12px; }}
    .mensaje {{ font-size: 15px; color: #475569; line-height: 1.6; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="card">
    <img class="logo" src="https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300" alt="ICA"/>
    <div class="icono">{icono}</div>
    <h1 class="titulo">{titulo}</h1>
    <p class="mensaje">{mensaje}</p>
    <p class="footer">Instituto de Cirugía Articular · Curicó, Chile</p>
  </div>
</body>
</html>"""

"""
modules/control/control_sobrecupo_router.py
"""

from __future__ import annotations

import json
import secrets
import os
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth
from agenda.store import load_store, save_store
from notifications.email_service import enviar_confirmacion_sobrecupo
from modules.pagos.flow_client import crear_pago
from modules.caja.caja_config_helper import get_valor_tipo

router = APIRouter(prefix="/api/sobrecupo", tags=["Sobre Cupo"])

TOKENS_PATH        = Path("/data/sobrecupo_tokens.json")
PROFESSIONALS_PATH = Path("/data/professionals.json")
LOCK               = Lock()
BASE_PACIENTES     = Path("/data/pacientes")

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://reservas.icarticular.cl")


# ============================================================
# HELPERS
# ============================================================

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


def _can_manage(user: dict, professional: str) -> bool:
    role_name = user.get("role", {}).get("name", "")
    if role_name == "secretaria":
        return True
    if role_name in ("medico", "kine"):
        return user.get("professional") == professional
    return False


# ============================================================
# SCHEMAS
# ============================================================

class CrearSobrecupoRequest(BaseModel):
    date:         str
    time:         str
    professional: str
    rut:          str
    gratuito:     bool = False


class EditarSobrecupoRequest(BaseModel):
    date:         str
    time:         str
    professional: str
    new_date:     Optional[str] = None
    new_time:     Optional[str] = None


class AceptarSobrecupoRequest(BaseModel):
    date:         str
    time:         str
    professional: str


# ============================================================
# 1. CREAR SOBRE CUPO
# ============================================================

@router.post("")
def crear_sobrecupo(
    data: CrearSobrecupoRequest,
    user=Depends(require_internal_auth)
):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="Solo puede gestionar su propio profesional")

    admin = _load_admin(data.rut)
    if not admin:
        raise HTTPException(status_code=404, detail="Ficha del paciente no encontrada")

    email = admin.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    with LOCK:
        store = load_store()

        existing = _get_slot(store, data.date, data.professional, data.time)
        if existing and existing.get("status") not in ("available", None, ""):
            raise HTTPException(status_code=409, detail=f"Ya existe un slot en {data.date} {data.time}")

        token = secrets.token_urlsafe(32)

        _set_slot_field(store, data.date, data.professional, data.time, {
            "status":               "reserved",
            "rut":                  data.rut,
            "sobrecupo":            True,
            "sobrecupo_gratuito":   data.gratuito,
            "sobrecupo_confirmado": False,
            "sobrecupo_aceptado":   False,
            "sobrecupo_token":      token,
            "sobrecupo_creado_por": user["usuario"],
            "sobrecupo_creado_at":  datetime.now(timezone.utc).isoformat(),
        })
        save_store(store)

        tokens = _load_tokens()
        tokens[token] = {
            "date":         data.date,
            "time":         data.time,
            "professional": data.professional,
            "rut":          data.rut,
            "gratuito":     data.gratuito,
            "created_at":   datetime.now(timezone.utc).isoformat(),
        }
        _save_tokens(tokens)

    nombre_paciente    = f"{admin.get('nombre', '')} {admin.get('apellido_paterno', '')}".strip()
    nombre_profesional = _get_professional_name(data.professional)

    # ── Generar link Flow si no es gratuito ─────────────────
    payment_url = None
    if not data.gratuito:
        try:
            id_pago = f"SC-{data.professional}-{data.date}-{data.time}-{token[:8]}"
            flow    = crear_pago(
                id_pago          = id_pago,
                amount           = get_valor_tipo(data.professional, "sobrecupo"),
                subject          = f"Sobre cupo {nombre_profesional} {data.date} {data.time}",
                email            = email,
                url_confirmation = f"{BACKEND_URL}/api/sobrecupo/pago/confirmar",
                url_return       = f"{FRONTEND_URL}/pago-sobrecupo?token={token}",
                optional_data    = {
                    "token_sobrecupo": token,
                    "professional":    data.professional,
                    "date":            data.date,
                    "time":            data.time,
                },
            )
            payment_url = f"{flow['url']}?token={flow['token']}"

            # Guardar flow_token en el slot
            with LOCK:
                store = load_store()
                _set_slot_field(store, data.date, data.professional, data.time, {
                    "flow_token":    flow["token"],
                    "flow_order":    flow.get("flowOrder"),
                    "payment_url":   payment_url,
                })
                save_store(store)

        except Exception as e:
            # No bloqueamos la creación si Flow falla — loguear y continuar
            print(f"[sobrecupo] Error Flow: {e}")

    # ── Enviar email ─────────────────────────────────────────
    ok = enviar_confirmacion_sobrecupo(
        email_paciente     = email,
        nombre_paciente    = nombre_paciente,
        fecha              = data.date,
        hora               = data.time,
        profesional_nombre = nombre_profesional,
        token              = token,
        gratuito           = data.gratuito,
        payment_url        = payment_url,
    )

    return {
        "ok":           True,
        "email_enviado": ok,
        "email":        email,
        "payment_url":  payment_url,
    }


# ============================================================
# 2. PACIENTE — confirma via link
# ============================================================

@router.get("/confirmar", response_class=HTMLResponse)
def confirmar_sobrecupo(token: str):
    with LOCK:
        tokens = _load_tokens()
        ref    = tokens.get(token)

        if not ref:
            return HTMLResponse(content=_html_page(
                titulo="Enlace inválido", mensaje="Este enlace ya fue usado o ha expirado.",
                color="#ef4444", icono="❌"
            ), status_code=404)

        store = load_store()
        slot  = _get_slot(store, ref["date"], ref["professional"], ref["time"])

        if not slot:
            return HTMLResponse(content=_html_page(
                titulo="Cita no encontrada", mensaje="No se encontró la cita asociada.",
                color="#ef4444", icono="❌"
            ), status_code=404)

        if slot.get("sobrecupo_confirmado"):
            return HTMLResponse(content=_html_page(
                titulo="Ya confirmado", mensaje="Su sobre cupo ya fue confirmado. ¡Gracias!",
                color="#16a34a", icono="✅"
            ))

        try:
            store["calendar"][ref["date"]][ref["professional"]]["slots"][ref["time"]]["sobrecupo_confirmado"] = True
        except KeyError:
            _set_slot_field(store, ref["date"], ref["professional"], ref["time"], {
                "sobrecupo_confirmado": True,
            })
        save_store(store)
        del tokens[token]
        _save_tokens(tokens)

    tipo = "gratuita" if ref.get("gratuito") else "con el valor normal de consulta"
    return HTMLResponse(content=_html_page(
        titulo="¡Confirmado!",
        mensaje=f"Su sobre cupo del {ref['date']} a las {ref['time']} fue confirmado. La atención será {tipo}. El médico ha sido notificado.",
        color="#16a34a", icono="✅"
    ))


# ============================================================
# 3. FLOW — confirmación de pago (webhook)
# ============================================================

@router.post("/pago/confirmar")
async def confirmar_pago_flow(request: Request):
    body       = await request.form()
    flow_token = body.get("token")
    if not flow_token:
        raise HTTPException(status_code=400, detail="Token Flow requerido")

    from modules.pagos.flow_client import obtener_estado_pago
    estado = obtener_estado_pago(flow_token)

    if estado.get("status") != 2:
        return {"ok": False, "status": estado.get("status")}

    optional = estado.get("optional", {})
    if isinstance(optional, str):
        import json as _json
        optional = _json.loads(optional)

    token_sobrecupo = optional.get("token_sobrecupo")
    professional    = optional.get("professional")
    date            = optional.get("date")
    time            = optional.get("time")

    if not all([token_sobrecupo, professional, date, time]):
        raise HTTPException(status_code=400, detail="Datos incompletos en optional")

    # Buscar monto y rut desde el slot
    store = load_store()
    slot  = _get_slot(store, date, professional, time)
    rut   = slot.get("rut", "")
    monto = get_valor_tipo(professional, "sobrecupo")

    with LOCK:
        store = load_store()
        _set_slot_field(store, date, professional, time, {
            "sobrecupo_confirmado": True,
            "pago_confirmado":      True,
            "pago_confirmado_at":   datetime.now(timezone.utc).isoformat(),
            "pagado":               True,
        })
        save_store(store)

        mes = date[:7]

        # Registrar en caja
        caja_path = Path("/data/caja") / f"{mes}.json"
        caja      = {}
        if caja_path.exists():
            with open(caja_path, "r", encoding="utf-8") as f:
                caja = json.load(f)
        caja.setdefault(date, {}).setdefault(professional, {})[time] = {
            "arrival_status": "paid",
            "pagado":         True,
            "tipo_atencion":  "sobrecupo",
            "monto":          monto,
            "es_gratuito":    False,
        }
        caja_path.parent.mkdir(parents=True, exist_ok=True)
        with open(caja_path, "w", encoding="utf-8") as f:
            json.dump(caja, f, indent=2, ensure_ascii=False)

        # Registrar en pagos
        pagos_path = Path("/data/pagos") / f"{mes}.json"
        pagos      = {}
        if pagos_path.exists():
            with open(pagos_path, "r", encoding="utf-8") as f:
                pagos = json.load(f)
        pagos.setdefault(date, {}).setdefault(professional, {})[time] = {
            "rut":              rut,
            "tipo_atencion":    "sobrecupo",
            "monto":            monto,
            "es_gratuito":      False,
            "metodo_pago":      "flow",
            "numero_operacion": str(estado.get("flowOrder", "")),
            "banco_origen":     None,
            "pagado_at":        datetime.now().isoformat(timespec="seconds"),
            "pagado_por":       "flow_online",
            "anulado":          False,
            "anulacion_motivo": None,
            "anulacion_at":     None,
            "anulado_por":      None,
        }
        pagos_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pagos_path, "w", encoding="utf-8") as f:
            json.dump(pagos, f, indent=2, ensure_ascii=False)

    return {"ok": True}


# ============================================================
# 4. MÉDICO — acepta sobre cupo
# ============================================================

@router.post("/aceptar")
def aceptar_sobrecupo(
    data: AceptarSobrecupoRequest,
    user=Depends(require_internal_auth)
):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="Solo puede gestionar su propio profesional")

    with LOCK:
        store = load_store()
        slot  = _get_slot(store, data.date, data.professional, data.time)

        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")
        if not slot.get("sobrecupo"):
            raise HTTPException(status_code=400, detail="Este slot no es un sobre cupo")
        if not slot.get("sobrecupo_confirmado"):
            raise HTTPException(status_code=400, detail="El paciente aún no ha confirmado")

        _set_slot_field(store, data.date, data.professional, data.time, {
            "sobrecupo_aceptado":     True,
            "sobrecupo_aceptado_por": user["usuario"],
            "sobrecupo_aceptado_at":  datetime.now(timezone.utc).isoformat(),
        })
        save_store(store)

    return {"ok": True}


# ============================================================
# 5. EDITAR SOBRE CUPO
# ============================================================

@router.put("/editar")
def editar_sobrecupo(
    data: EditarSobrecupoRequest,
    user=Depends(require_internal_auth)
):
    if not _can_manage(user, data.professional):
        raise HTTPException(status_code=403, detail="Solo puede gestionar su propio profesional")

    if not data.new_date and not data.new_time:
        raise HTTPException(status_code=400, detail="Debe indicar nueva fecha o nueva hora")

    with LOCK:
        store = load_store()
        slot  = _get_slot(store, data.date, data.professional, data.time)

        if not slot:
            raise HTTPException(status_code=404, detail="Slot no encontrado")
        if not slot.get("sobrecupo"):
            raise HTTPException(status_code=400, detail="Este slot no es un sobre cupo")

        new_date = data.new_date or data.date
        new_time = data.new_time or data.time

        if new_date == data.date and new_time == data.time:
            raise HTTPException(status_code=400, detail="La fecha y hora son iguales")

        existing = _get_slot(store, new_date, data.professional, new_time)
        if existing and existing.get("status") not in ("available", None, ""):
            raise HTTPException(status_code=409, detail=f"Ya existe un slot en {new_date} {new_time}")

        slot_data = dict(slot)
        slot_data.update({
            "sobrecupo_editado_por": user["usuario"],
            "sobrecupo_editado_at":  datetime.now(timezone.utc).isoformat(),
            "sobrecupo_confirmado":  False,
            "sobrecupo_aceptado":    False,
        })

        _set_slot_field(store, new_date, data.professional, new_time, slot_data)
        del store["calendar"][data.date][data.professional]["slots"][data.time]
        save_store(store)

        tokens = _load_tokens()
        for t, ref in tokens.items():
            if ref["date"] == data.date and ref["time"] == data.time and ref["professional"] == data.professional:
                ref["date"] = new_date
                ref["time"] = new_time
                break
        _save_tokens(tokens)

    return {"ok": True, "new_date": new_date, "new_time": new_time}


# ============================================================
# HTML helper
# ============================================================

def _html_page(titulo: str, mensaje: str, color: str, icono: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Instituto de Cirugía Articular</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f8fafc; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }}
    .card {{ background: #fff; border-radius: 16px; padding: 40px 32px; max-width: 420px; width: 100%; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
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
        

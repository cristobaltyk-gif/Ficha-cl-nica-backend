"""
modules/pagos/confirmacion_router.py

Endpoints:
1. GET  /api/confirmar-asistencia?token=...  → paciente confirma + link pago
2. POST /api/flow/webhook                    → Flow notifica pago
3. GET  /api/flow/retorno                    → paciente vuelve tras pagar
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Confirmación y Pagos"])

TOKENS_PATH     = Path("/data/confirmacion_tokens.json")
PAGOS_FLOW_PATH = Path("/data/pagos_flow.json")
AGENDA_PATH     = Path("/data/agenda_future.json")
PAGOS_DIR       = Path("/data/pagos")
CAJA_DIR        = Path("/data/caja")
LOCK            = Lock()

BACKEND_URL  = os.getenv("BACKEND_URL", "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URLS", "https://clinica.icarticular.cl").split(",")[0].strip()

LOGO_URL = "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _set_slot_fields(date: str, professional: str, time: str, updates: dict) -> None:
    store = _load_json(AGENDA_PATH)
    slot  = (
        store["calendar"]
             .setdefault(date, {})
             .setdefault(professional, {"schedule": {}, "slots": {}})
             ["slots"]
             .setdefault(time, {})
    )
    slot.update(updates)
    _save_json(AGENDA_PATH, store)


def _html(titulo: str, contenido: str, color: str, icono: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Instituto de Cirugía Articular</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Helvetica Neue',Arial,sans-serif;background:#f8fafc;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
    .card{{background:#fff;border-radius:16px;padding:40px 32px;max-width:440px;width:100%;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,.08)}}
    .logo{{height:50px;margin-bottom:24px}}
    .icono{{font-size:52px;margin-bottom:20px}}
    .titulo{{font-size:22px;font-weight:700;color:{color};margin-bottom:12px}}
    .contenido{{font-size:15px;color:#475569;line-height:1.6}}
    .btn{{display:inline-block;margin-top:24px;background:#0f172a;color:white;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px}}
    .footer{{margin-top:32px;font-size:12px;color:#94a3b8}}
  </style>
</head>
<body>
  <div class="card">
    <img class="logo" src="{LOGO_URL}" alt="ICA"/>
    <div class="icono">{icono}</div>
    <h1 class="titulo">{titulo}</h1>
    <div class="contenido">{contenido}</div>
    <p class="footer">Instituto de Cirugía Articular · Curicó, Chile</p>
  </div>
</body>
</html>"""


# ======================================================
# 1. PACIENTE CONFIRMA ASISTENCIA
# ======================================================

@router.get("/api/confirmar-asistencia", response_class=HTMLResponse)
def confirmar_asistencia(token: str):
    with LOCK:
        tokens = _load_json(TOKENS_PATH)
        ref    = tokens.get(token)

        if not ref:
            return HTMLResponse(content=_html(
                "Enlace inválido", "Este enlace ya fue usado o ha expirado.", "#ef4444", "❌"
            ), status_code=404)

        # Confirmar asistencia → slot confirmed
        _set_slot_fields(ref["date"], ref["professional"], ref["time"], {
            "status":                "confirmed",
            "asistencia_confirmada": True,
        })

        del tokens[token]
        _save_json(TOKENS_PATH, tokens)

    # Generar link de pago Flow si hay monto
    monto     = ref.get("monto", 0)
    link_pago = None

    if monto > 0:
        try:
            from modules.pagos.flow_client import crear_pago
            pago_id  = f"ICA-{ref['date']}-{ref['professional']}-{ref['time'].replace(':','')}"
            resultado = crear_pago(
                id_pago=pago_id,
                amount=monto,
                subject=f"Consulta ICA · {ref['date']} {ref['time']}",
                email=ref.get("email", ""),
                url_confirmation=f"{BACKEND_URL}/api/flow/webhook",
                url_return=f"{BACKEND_URL}/api/flow/retorno",
                optional_data={
                    "date":         ref["date"],
                    "time":         ref["time"],
                    "professional": ref["professional"],
                    "rut":          ref.get("rut", ""),
                    "tipo_atencion": ref.get("tipo_atencion", "particular"),
                }
            )
            link_pago = f"{resultado['url']}?token={resultado['token']}"

            pagos_flow = _load_json(PAGOS_FLOW_PATH)
            pagos_flow[resultado["token"]] = {
                "date":         ref["date"],
                "time":         ref["time"],
                "professional": ref["professional"],
                "rut":          ref.get("rut", ""),
                "email":        ref.get("email", ""),
                "monto":        monto,
                "tipo_atencion": ref.get("tipo_atencion", "particular"),
                "created_at":   datetime.now(timezone.utc).isoformat()
            }
            _save_json(PAGOS_FLOW_PATH, pagos_flow)

        except Exception as e:
            print(f"⚠️ Error creando pago Flow: {e}")

    if link_pago:
        contenido = f"""
        <p>Su asistencia para el <strong>{ref['date']}</strong> a las <strong>{ref['time']}</strong> ha sido confirmada.</p>
        <p style="margin-top:12px;">Para agilizar su atención puede pagar ahora en línea:</p>
        <a href="{link_pago}" class="btn">💳 Pagar en línea</a>
        <p style="margin-top:16px;font-size:13px;color:#94a3b8;">También puede pagar al llegar al centro.</p>
        """
    else:
        contenido = f"""
        <p>Su asistencia para el <strong>{ref['date']}</strong> a las <strong>{ref['time']}</strong> ha sido confirmada.</p>
        <p style="margin-top:12px;">Le esperamos en el Instituto de Cirugía Articular.</p>
        """

    return HTMLResponse(content=_html("¡Asistencia confirmada!", contenido, "#166534", "✅"))


# ======================================================
# 2. WEBHOOK FLOW
# ======================================================

@router.post("/api/flow/webhook")
async def flow_webhook(request: Request):
    form  = await request.form()
    token = form.get("token")

    if not token:
        return {"ok": False}

    try:
        from modules.pagos.flow_client import obtener_estado_pago
        estado = obtener_estado_pago(token)

        if estado.get("status") != 2:
            return {"ok": False, "status": estado.get("status")}

        pagos_flow = _load_json(PAGOS_FLOW_PATH)
        ref        = pagos_flow.get(token)

        if not ref:
            return {"ok": False, "error": "token no encontrado"}

        with LOCK:
            _set_slot_fields(ref["date"], ref["professional"], ref["time"], {
                "pagado":      True,
                "pagado_flow": True,
            })

            mes = ref["date"][:7]

            # Registrar en caja
            caja_path = CAJA_DIR / f"{mes}.json"
            caja      = _load_json(caja_path)
            caja.setdefault(ref["date"], {}).setdefault(ref["professional"], {})[ref["time"]] = {
                "arrival_status": "paid",
                "pagado":         True,
                "tipo_atencion":  ref.get("tipo_atencion", "particular"),
                "monto":          ref["monto"],
                "es_gratuito":    False,
            }
            _save_json(caja_path, caja)

            # Registrar en pagos
            pagos_path = PAGOS_DIR / f"{mes}.json"
            pagos      = _load_json(pagos_path)
            pagos.setdefault(ref["date"], {}).setdefault(ref["professional"], {})[ref["time"]] = {
                "rut":              ref.get("rut", ""),
                "tipo_atencion":    ref.get("tipo_atencion", "particular"),
                "monto":            ref["monto"],
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
            _save_json(pagos_path, pagos)

        # Email de confirmación de pago
        email = ref.get("email", "")
        if email:
            try:
                from notifications.email_pagos import enviar_confirmacion_pago
                from modules.pagos.flow_client import obtener_estado_pago as get_estado
                rut = ref.get("rut", "")
                admin_path = Path("/data/pacientes") / rut / "admin.json"
                nombre = rut
                if admin_path.exists():
                    with open(admin_path) as f:
                        admin = json.load(f)
                    nombre = f"{admin.get('nombre','')} {admin.get('apellido_paterno','')}".strip()
                from modules.pagos.flow_client import _get_professional_name_safe
                enviar_confirmacion_pago(
                    email_paciente=email,
                    nombre_paciente=nombre,
                    fecha=ref["date"],
                    hora=ref["time"],
                    profesional_nombre=ref["professional"],
                    monto=ref["monto"],
                    numero_orden=str(estado.get("flowOrder", ""))
                )
            except Exception as e:
                print(f"⚠️ Error enviando email pago: {e}")

        return {"ok": True}

    except Exception as e:
        print(f"❌ ERROR webhook Flow: {e}")
        return {"ok": False, "error": str(e)}


# ======================================================
# 3. RETORNO FLOW
# ======================================================

@router.get("/api/flow/retorno", response_class=HTMLResponse)
async def flow_retorno(request: Request):
    token = request.query_params.get("token", "")
    try:
        from modules.pagos.flow_client import obtener_estado_pago
        estado = obtener_estado_pago(token)
        pagado = estado.get("status") == 2
    except:
        pagado = False

    if pagado:
        return HTMLResponse(content=_html(
            "¡Pago exitoso!",
            "Su pago ha sido procesado. Le esperamos en el Instituto de Cirugía Articular.",
            "#166534", "✅"
        ))
    return HTMLResponse(content=_html(
        "Pago pendiente",
        "Su pago está siendo procesado. También puede pagar al llegar al centro.",
        "#1e40af", "⏳"
    ))
  

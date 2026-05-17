"""
modules/suscripciones/suscripcion_router.py
Solo maneja el webhook de confirmación de pago Flow.
Crear, cobrar y gestionar suscripciones es responsabilidad del superadmin.
"""
from __future__ import annotations

import os
import json
import secrets
from datetime import date, timedelta
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from db.supabase_client import get_suscripcion, update_suscripcion

router = APIRouter(prefix="/api/suscripciones", tags=["Suscripciones"])

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://admin.icarticular.cl")


@router.get("/tipo")
async def get_tipo(scope: str):
    s = get_suscripcion(scope)
    if not s:
        return {"tipo": "externo_completo"}
    return {"tipo": s.get("plan", "externo_completo")}


@router.api_route("/retorno", methods=["GET", "POST"])
async def retorno_suscripcion(request: Request):
    token = request.query_params.get("token", "")
    if request.method == "POST":
        form  = await request.form()
        token = form.get("token", token)
    return RedirectResponse(
        url=f"{FRONTEND_URL}/pago-exitoso?token={token}",
        status_code=302
    )


@router.get("/retorno-info")
async def retorno_info(token: str):
    try:
        from modules.pagos.flow_client import obtener_estado_pago
        estado   = obtener_estado_pago(token)
        optional = estado.get("optional", {})
        if isinstance(optional, str):
            optional = json.loads(optional)
        centro_id = optional.get("centro_id")
        if not centro_id:
            return {"ok": False}
        s = get_suscripcion(centro_id)
        if not s:
            return {"ok": False}
        return {
            "ok":    True,
            "email": s.get("email_contacto", ""),
            "nombre": s.get("nombre_centro", ""),
        }
    except Exception:
        return {"ok": False}


@router.post("/webhook/pago")
async def webhook_pago(request: Request):
    body  = await request.form()
    token = body.get("token")
    if not token:
        return {"ok": False}

    from modules.pagos.flow_client import obtener_estado_pago
    estado = obtener_estado_pago(token)

    if estado.get("status") != 2:
        return {"ok": False, "status": estado.get("status")}

    optional = estado.get("optional", {})
    if isinstance(optional, str):
        optional = json.loads(optional)

    centro_id = optional.get("centro_id")
    if not centro_id:
        return {"ok": False}

    s = get_suscripcion(centro_id)
    if not s:
        return {"ok": False, "error": "Suscripción no encontrada"}

    nueva_fecha    = (date.today() + timedelta(days=30)).isoformat()
    es_primer_pago = s.get("estado") == "pendiente_pago"
    era_suspendido = s.get("estado") == "suspendido"

    update_suscripcion(centro_id, {
        "estado":            "activo",
        "fecha_vencimiento": nueva_fecha
    })
    print(f"[WEBHOOK] ✅ Suscripción {centro_id} activada hasta {nueva_fecha}")

    if era_suspendido:
        try:
            from modules.suscripciones.suscripcion_scheduler import _reactivar_usuarios_centro
            _reactivar_usuarios_centro(centro_id)
        except Exception as e:
            print(f"[WEBHOOK] Error reactivando usuarios: {e}")

    if es_primer_pago:
        try:
            username, password_temp = _crear_usuario_admin_centro(centro_id, s)
            plan = s.get("plan", "centro")
            if plan == "centro":
                from notifications.email_suscripciones import enviar_credenciales_acceso
                enviar_credenciales_acceso(
                    email_contacto=s["email_contacto"],
                    nombre_centro=s["nombre_centro"],
                    username_admin=username,
                    password_temp=password_temp,
                    plan=plan,
                    max_usuarios=s.get("roles", {}),
                )
            else:
                from notifications.email_suscripciones import enviar_credenciales_externo
                enviar_credenciales_externo(
                    email_contacto=s["email_contacto"],
                    nombre=s["nombre_centro"],
                    username=username,
                    password_temp=password_temp,
                    plan=plan,
                )
            print(f"[WEBHOOK] ✅ Credenciales enviadas a {s['email_contacto']}")
        except Exception as e:
            print(f"[WEBHOOK] Error creando usuario: {e}")

    return {"ok": True}


def _crear_usuario_admin_centro(centro_id: str, s: dict) -> tuple[str, str]:
    from db.supabase_client import get_users, save_user

    plan = s.get("plan", "centro")

    if plan == "centro":
        username = f"admin_{centro_id}"
        role = {
            "name":  "admin",
            "entry": "/admin",
            "allow": ["agenda", "pacientes", "atencion", "documentos", "administracion"],
            "scope": centro_id,
        }
    elif plan == "externo_completo":
        username = centro_id
        role = {
            "name":  "medico",
            "entry": "/medico",
            "allow": ["agenda", "pacientes", "atencion", "documentos"],
            "scope": centro_id,
        }
    else:
        username = centro_id
        role = {
            "name":  "medico",
            "entry": "/medico",
            "allow": ["agenda", "pacientes", "atencion", "documentos"],
            "scope": "externo",
        }

    password = secrets.token_urlsafe(10)
    users    = get_users()

    if username not in users:
        save_user(username, {
            "password":     password,
            "active":       True,
            "professional": centro_id,
            "role":         role,
        })
        print(f"[WEBHOOK] Usuario creado: {username} — plan: {plan}")
    else:
        password = secrets.token_urlsafe(10)
        users[username]["password"] = password
        save_user(username, users[username])

    return username, password

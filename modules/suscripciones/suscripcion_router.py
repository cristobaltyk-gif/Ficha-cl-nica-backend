"""
modules/suscripciones/suscripcion_router.py
Solo maneja el webhook de confirmación de pago Flow.
Crear, cobrar y gestionar suscripciones es responsabilidad del superadmin.
"""
from __future__ import annotations

import os
import secrets
from datetime import date, timedelta
from fastapi import APIRouter, Request

from db.supabase_client import get_suscripcion, update_suscripcion

router = APIRouter(prefix="/api/suscripciones", tags=["Suscripciones"])

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://clinica.icarticular.cl")


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK FLOW — confirma pago, activa suscripción, crea admin y envía credenciales
# ══════════════════════════════════════════════════════════════════════════════

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
        import json
        optional = json.loads(optional)

    centro_id = optional.get("centro_id")
    if not centro_id:
        return {"ok": False}

    s = get_suscripcion(centro_id)
    if not s:
        return {"ok": False, "error": "Suscripción no encontrada"}

    nueva_fecha    = (date.today() + timedelta(days=30)).isoformat()
    es_primer_pago = s.get("estado") == "pendiente_pago"

    # Activar suscripción
    update_suscripcion(centro_id, {
        "estado":            "activo",
        "fecha_vencimiento": nueva_fecha
    })
    print(f"[WEBHOOK] ✅ Suscripción {centro_id} activada hasta {nueva_fecha}")

    # Si es primer pago → crear usuario admin y enviar credenciales
    if es_primer_pago:
        try:
            username_admin, password_temp = _crear_usuario_admin_centro(centro_id, s)
            from notifications.email_suscripciones import enviar_credenciales_acceso
            enviar_credenciales_acceso(
                email_contacto=s["email_contacto"],
                nombre_centro=s["nombre_centro"],
                username_admin=username_admin,
                password_temp=password_temp,
                plan=s["plan"],
                max_usuarios=s.get("roles", {}),
            )
            print(f"[WEBHOOK] ✅ Credenciales enviadas a {s['email_contacto']}")
        except Exception as e:
            print(f"[WEBHOOK] Error creando usuario admin: {e}")

    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _crear_usuario_admin_centro(centro_id: str, s: dict) -> tuple[str, str]:
    """Crea el usuario admin del centro con clave temporal."""
    from db.supabase_client import get_users, save_user

    username = f"admin_{centro_id}"
    password = secrets.token_urlsafe(10)

    users = get_users()
    if username not in users:
        save_user(username, {
            "password":     password,
            "active":       True,
            "professional": "system",
            "role": {
                "name":  "admin",
                "entry": "/admin",
                "allow": ["agenda", "pacientes", "atencion", "documentos", "administracion"],
                "scope": centro_id,
            }
        })
        print(f"[WEBHOOK] Usuario admin creado: {username}")
    else:
        # Ya existe — regenerar clave
        password = secrets.token_urlsafe(10)
        users[username]["password"] = password
        save_user(username, users[username])

    return username, password
    

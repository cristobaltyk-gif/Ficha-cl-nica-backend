"""
modules/suscripciones/suscripcion_router.py
"""
from __future__ import annotations

import os
import secrets
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict

from auth.internal_auth import require_internal_auth
from db.supabase_client import (
    get_suscripcion, get_all_suscripciones, save_suscripcion,
    update_suscripcion, calcular_precio_centro, PRECIOS_EXTERNO
)

router = APIRouter(prefix="/api/suscripciones", tags=["Suscripciones"])

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://clinica.icarticular.cl")


class CrearSuscripcionRequest(BaseModel):
    centro_id:        str
    nombre_centro:    str
    plan:             str
    roles:            Dict[str, int] = {}
    email_contacto:   str
    descuento_pct:    int = 0
    descuento_motivo: str = ""
    descuento_hasta:  Optional[str] = None
    metodo_pago:      str = "manual"


class ActualizarDescuentoRequest(BaseModel):
    descuento_pct:    int
    descuento_motivo: str = ""
    descuento_hasta:  Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# LECTURA
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
def listar_suscripciones(auth=Depends(require_internal_auth)):
    if auth["role"]["name"] != "admin":
        raise HTTPException(403, "Solo admin")
    return get_all_suscripciones()


@router.get("/{centro_id}")
def get_suscripcion_endpoint(centro_id: str, auth=Depends(require_internal_auth)):
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")
    return s


# ══════════════════════════════════════════════════════════════════════════════
# CREAR
# ══════════════════════════════════════════════════════════════════════════════

@router.post("")
def crear_suscripcion(data: CrearSuscripcionRequest, auth=Depends(require_internal_auth)):
    if auth["role"]["name"] != "admin":
        raise HTTPException(403, "Solo admin")

    hoy = date.today()

    if data.plan == "centro":
        precios = calcular_precio_centro(data.roles, data.descuento_pct)
    else:
        precio_base = PRECIOS_EXTERNO.get(data.plan, 35000)
        descuento   = int(precio_base * data.descuento_pct / 100)
        precios = {
            "precio_base":  precio_base,
            "precio_final": precio_base - descuento,
        }

    suscripcion = {
        "centro_id":           data.centro_id,
        "nombre_centro":       data.nombre_centro,
        "plan":                data.plan,
        "roles":               data.roles,
        "precio_base":         precios["precio_base"],
        "descuento_pct":       data.descuento_pct,
        "descuento_motivo":    data.descuento_motivo,
        "descuento_hasta":     data.descuento_hasta,
        "precio_final":        precios["precio_final"],
        "estado":              "pendiente_pago",
        "fecha_inicio":        hoy.isoformat(),
        "fecha_vencimiento":   (hoy + timedelta(days=30)).isoformat(),
        "email_contacto":      data.email_contacto,
        "metodo_pago":         data.metodo_pago,
        "flow_customer_id":    None,
        "flow_subscription_id":None,
    }

    save_suscripcion(suscripcion)

    if data.metodo_pago == "automatico":
        try:
            flow_url = _registrar_cliente_flow(data.centro_id, data.email_contacto)
            return {"ok": True, "flow_registro_url": flow_url, **suscripcion}
        except Exception as e:
            return {"ok": True, "warning": f"Flow: {e}", **suscripcion}

    try:
        link = _generar_link_pago(data.centro_id, precios["precio_final"], data.email_contacto)
        # Enviar email con link de pago
        try:
            from notifications.email_suscripciones import enviar_link_primer_pago
            enviar_link_primer_pago(
                email_contacto=data.email_contacto,
                nombre_centro=data.nombre_centro,
                monto=precios["precio_final"],
                link_pago=link,
                fecha_vencimiento=suscripcion["fecha_vencimiento"],
            )
        except Exception as e:
            print(f"[SUSCRIPCIONES] Error enviando email primer pago: {e}")
        return {"ok": True, "link_pago": link, **suscripcion}
    except Exception as e:
        return {"ok": True, "warning": f"Flow: {e}", **suscripcion}


# ══════════════════════════════════════════════════════════════════════════════
# DESCUENTO
# ══════════════════════════════════════════════════════════════════════════════

@router.patch("/{centro_id}/descuento")
def aplicar_descuento(
    centro_id: str,
    data: ActualizarDescuentoRequest,
    auth=Depends(require_internal_auth)
):
    if auth["role"]["name"] != "admin":
        raise HTTPException(403, "Solo admin")
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")
    precio_final = int(s["precio_base"] * (1 - data.descuento_pct / 100))
    update_suscripcion(centro_id, {
        "descuento_pct":    data.descuento_pct,
        "descuento_motivo": data.descuento_motivo,
        "descuento_hasta":  data.descuento_hasta,
        "precio_final":     precio_final,
    })
    return {"ok": True, "precio_final": precio_final}


# ══════════════════════════════════════════════════════════════════════════════
# COBRAR
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{centro_id}/cobrar")
def cobrar_suscripcion(centro_id: str, auth=Depends(require_internal_auth)):
    if auth["role"]["name"] != "admin":
        raise HTTPException(403, "Solo admin")
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")

    precio_final = s["precio_final"]
    if s.get("descuento_hasta") and date.today().isoformat() > s["descuento_hasta"]:
        precio_final = s["precio_base"]
        update_suscripcion(centro_id, {
            "descuento_pct": 0, "descuento_motivo": "",
            "descuento_hasta": None, "precio_final": precio_final
        })

    try:
        from modules.pagos.flow_client import _make_signature, FLOW_BASE_URL, FLOW_API_KEY
        import httpx, json

        if s.get("flow_customer_id"):
            params = {
                "apiKey":            FLOW_API_KEY,
                "customerId":        s["flow_customer_id"],
                "amount":            str(precio_final),
                "subject":           f"Suscripción {s['nombre_centro']} — {date.today().strftime('%B %Y')}",
                "urlConfirmation":   f"{BACKEND_URL}/api/suscripciones/webhook/pago",
                "optional":          json.dumps({"centro_id": centro_id}),
            }
            params["s"] = _make_signature(params)
            with httpx.Client(timeout=30) as client:
                res = client.post(f"{FLOW_BASE_URL}/customer/collect", data=params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
            return {"ok": True, "flow": res.json()}
        else:
            link = _generar_link_pago(centro_id, precio_final, s["email_contacto"])
            return {"ok": True, "link_pago": link}
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK FLOW — confirma pago, activa suscripción, envía credenciales
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

    nueva_fecha = (date.today() + timedelta(days=30)).isoformat()
    es_primer_pago = s.get("estado") == "pendiente_pago"

    # Activar suscripción
    update_suscripcion(centro_id, {
        "estado":            "activo",
        "fecha_vencimiento": nueva_fecha
    })

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
    password = secrets.token_urlsafe(10)  # clave temporal legible

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
        # Ya existe — generar nueva clave temporal
        password = secrets.token_urlsafe(10)
        users[username]["password"] = password
        save_user(username, users[username])

    return username, password


def _registrar_cliente_flow(centro_id: str, email: str) -> str:
    from modules.pagos.flow_client import _assert_env, _make_signature, FLOW_BASE_URL, FLOW_API_KEY
    import httpx
    _assert_env()

    params = {"apiKey": FLOW_API_KEY, "externalId": centro_id, "email": email}
    params["s"] = _make_signature(params)
    with httpx.Client(timeout=30) as client:
        res = client.post(f"{FLOW_BASE_URL}/customer/create", data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
    customer    = res.json()
    customer_id = customer.get("customerId")
    if customer_id:
        update_suscripcion(centro_id, {"flow_customer_id": customer_id})

    params2 = {
        "apiKey":     FLOW_API_KEY,
        "customerId": customer_id,
        "url_return": f"{FRONTEND_URL}/suscripcion?centro={centro_id}",
    }
    params2["s"] = _make_signature(params2)
    with httpx.Client(timeout=30) as client:
        res2 = client.post(f"{FLOW_BASE_URL}/customer/register", data=params2,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
    data2 = res2.json()
    return f"{data2.get('url')}?token={data2.get('token')}"


def _generar_link_pago(centro_id: str, monto: int, email: str) -> str:
    from modules.pagos.flow_client import crear_pago
    mes    = date.today().strftime("%Y-%m")
    result = crear_pago(
        id_pago=f"SUB-{centro_id}-{mes}",
        amount=monto,
        subject=f"Suscripción sistema clínico — {mes}",
        email=email,
        url_confirmation=f"{BACKEND_URL}/api/suscripciones/webhook/pago",
        url_return=f"{FRONTEND_URL}/suscripcion?centro={centro_id}",
        optional_data={"centro_id": centro_id},
    )
    return f"{result['url']}?token={result['token']}"
        

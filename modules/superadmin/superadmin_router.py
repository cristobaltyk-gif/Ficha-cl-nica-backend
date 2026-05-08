"""
modules/superadmin/superadmin_router.py
Endpoints exclusivos del superadministrador de la plataforma.
Protegidos por API key — no por usuarios de BD.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from auth.superadmin_auth import require_superadmin
from db.supabase_client import (
    _get_conn,
    get_all_suscripciones,
    save_suscripcion,
    update_suscripcion,
    get_suscripcion,
    calcular_precio_centro,
    PRECIOS_EXTERNO,
    get_users,
    save_user,
)

router = APIRouter(
    prefix="/api/superadmin",
    tags=["Superadmin"],
    dependencies=[Depends(require_superadmin)]
)

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://admin.icarticular.cl")


# ══════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard():
    suscripciones = get_all_suscripciones()
    activas  = [s for s in suscripciones if s.get("estado") == "activo"]
    vencidas = [s for s in suscripciones if s.get("estado") == "vencido"]
    mrr      = sum(s.get("precio_final", 0) for s in activas)

    users = get_users()
    usuarios_activos = sum(1 for u in users.values() if u.get("active", True))

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM profesionales WHERE active = TRUE")
            total_profesionales = cur.fetchone()["total"]

    return {
        "centros_activos":     len(activas),
        "centros_vencidos":    len(vencidas),
        "mrr":                 mrr,
        "usuarios_activos":    usuarios_activos,
        "total_profesionales": total_profesionales,
    }


# ══════════════════════════════════════════════════════════════
# SUSCRIPCIONES
# ══════════════════════════════════════════════════════════════

@router.get("/suscripciones")
def listar_suscripciones():
    return get_all_suscripciones()


@router.post("/suscripciones")
def crear_suscripcion(data: dict):
    centro_id = data.get("centro_id")
    if not centro_id:
        raise HTTPException(400, "Falta centro_id")

    plan     = data.get("plan", "centro")
    roles    = data.get("roles", {})
    desc_pct = data.get("descuento_pct", 0)

    if plan == "centro":
        precios = calcular_precio_centro(roles, desc_pct)
    else:
        precio_base = PRECIOS_EXTERNO.get(plan, 35000)
        descuento   = int(precio_base * desc_pct / 100)
        precios = {
            "precio_base":  precio_base,
            "precio_final": precio_base - descuento,
        }

    hoy = date.today()
    suscripcion = {
        "centro_id":           centro_id,
        "nombre_centro":       data.get("nombre_centro", centro_id),
        "plan":                plan,
        "roles":               roles,
        "precio_base":         precios["precio_base"],
        "descuento_pct":       desc_pct,
        "descuento_motivo":    data.get("descuento_motivo", ""),
        "descuento_hasta":     data.get("descuento_hasta"),
        "precio_final":        precios["precio_final"],
        "estado":              "pendiente_pago",
        "fecha_inicio":        hoy.isoformat(),
        "fecha_vencimiento":   (hoy + timedelta(days=30)).isoformat(),
        "email_contacto":      data.get("email_contacto", ""),
        "metodo_pago":         data.get("metodo_pago", "manual"),
        "flow_customer_id":    None,
        "flow_subscription_id":None,
    }

    save_suscripcion(suscripcion)

    # Generar link de pago y enviar email
    if precios["precio_final"] > 0 and data.get("email_contacto"):
        try:
            link = _generar_link_pago(centro_id, precios["precio_final"], data.get("email_contacto", ""))
            try:
                from notifications.email_suscripciones import enviar_link_primer_pago
                enviar_link_primer_pago(
                    email_contacto=data.get("email_contacto", ""),
                    nombre_centro=data.get("nombre_centro", centro_id),
                    monto=precios["precio_final"],
                    link_pago=link,
                    fecha_vencimiento=suscripcion["fecha_vencimiento"],
                )
                print(f"[SUPERADMIN] ✅ Email primer pago enviado a {data.get('email_contacto')}")
            except Exception as e:
                print(f"[SUPERADMIN] Error email primer pago: {e}")
            return {"ok": True, "link_pago": link}
        except Exception as e:
            print(f"[SUPERADMIN] ❌ Error generando link Flow: {e}")
            # Intentar enviar email sin link si hay email
            try:
                from notifications.email_suscripciones import enviar_link_primer_pago
                enviar_link_primer_pago(
                    email_contacto=data.get("email_contacto", ""),
                    nombre_centro=data.get("nombre_centro", centro_id),
                    monto=precios["precio_final"],
                    link_pago="— Link no disponible, contactar a contacto@icarticular.cl —",
                    fecha_vencimiento=suscripcion["fecha_vencimiento"],
                )
            except Exception as e2:
                print(f"[SUPERADMIN] ❌ Error email sin link: {e2}")
            return {"ok": True, "warning": str(e)}

    return {"ok": True}


@router.delete("/suscripciones/{centro_id}")
def borrar_suscripcion(centro_id: str):
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM suscripciones WHERE centro_id = %s", (centro_id,))
            conn.commit()
    return {"ok": True, "deleted": centro_id}


@router.patch("/suscripciones/{centro_id}/roles")
def modificar_roles(centro_id: str, data: dict):
    """Modifica los roles/cantidad de una suscripción y recalcula el precio."""
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")

    roles    = data.get("roles", s.get("roles", {}))
    desc_pct = s.get("descuento_pct", 0)

    if s.get("plan") == "centro":
        precios = calcular_precio_centro(roles, desc_pct)
    else:
        precio_base = PRECIOS_EXTERNO.get(s["plan"], 35000)
        precios = {
            "precio_base":  precio_base,
            "precio_final": precio_base - int(precio_base * desc_pct / 100),
        }

    import json as _json
    update_suscripcion(centro_id, {
        "roles":       _json.dumps(roles) if isinstance(roles, dict) else roles,
        "precio_base": precios["precio_base"],
        "precio_final":precios["precio_final"],
    })

    # Actualizar también en tabla centros si existe
    try:
        from db.supabase_client import get_centro, save_centro
        centro = get_centro(centro_id)
        if centro:
            centro["max_usuarios"] = roles
            save_centro(centro)
    except Exception as e:
        print(f"[SUPERADMIN] Error actualizando centro: {e}")

    return {
        "ok":          True,
        "roles":       roles,
        "precio_base": precios["precio_base"],
        "precio_final":precios["precio_final"],
    }


@router.patch("/suscripciones/{centro_id}/estado")
def cambiar_estado(centro_id: str, data: dict):
    estado = data.get("estado")
    if estado not in ("activo", "vencido", "suspendido"):
        raise HTTPException(400, "Estado inválido")
    update_suscripcion(centro_id, {"estado": estado})
    return {"ok": True}


@router.patch("/suscripciones/{centro_id}/descuento")
def aplicar_descuento(centro_id: str, data: dict):
    update_suscripcion(centro_id, {
        "descuento_pct":   data.get("descuento_pct", 0),
        "descuento_motivo":data.get("descuento_motivo", ""),
        "descuento_hasta": data.get("descuento_hasta"),
        "precio_final":    data.get("precio_final", 0),
    })
    return {"ok": True}




@router.patch("/suscripciones/{centro_id}")
def modificar_suscripcion(centro_id: str, data: dict):
    """Modifica cualquier campo de la suscripción — superadmin tiene control total."""
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")

    # Si cambian roles → recalcular precio
    if "roles" in data and s.get("plan") == "centro":
        roles    = data["roles"]
        desc_pct = data.get("descuento_pct", s.get("descuento_pct", 0))
        precios  = calcular_precio_centro(roles, desc_pct)
        data["precio_base"]  = precios["precio_base"]
        data["precio_final"] = precios["precio_final"]
        try:
            from db.supabase_client import get_centro, save_centro
            centro = get_centro(centro_id)
            if centro:
                centro["max_usuarios"] = roles
                save_centro(centro)
        except Exception as e:
            print(f"[SUPERADMIN] Error actualizando centro: {e}")
    elif "descuento_pct" in data and "roles" not in data:
        desc_pct = data["descuento_pct"]
        data["precio_final"] = int(s["precio_base"] * (1 - desc_pct / 100))

    import json
    # Serializar campos dict para PostgreSQL
    if "roles" in data and isinstance(data["roles"], dict):
        data["roles"] = json.dumps(data["roles"])

    update_suscripcion(centro_id, data)
    return {"ok": True}

@router.post("/suscripciones/{centro_id}/cobrar")
def cobrar_suscripcion(centro_id: str):
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")

    # Verificar descuento vencido
    precio_final = s["precio_final"]
    if s.get("descuento_hasta") and date.today().isoformat() > s["descuento_hasta"]:
        precio_final = s["precio_base"]
        update_suscripcion(centro_id, {
            "descuento_pct": 0, "descuento_motivo": "",
            "descuento_hasta": None, "precio_final": precio_final
        })

    try:
        link = _generar_link_pago(centro_id, precio_final, s["email_contacto"])
        # Enviar email con link de cobro
        try:
            from notifications.email_suscripciones import enviar_recordatorio_renovacion
            enviar_recordatorio_renovacion(
                email_contacto=s["email_contacto"],
                nombre_centro=s["nombre_centro"],
                monto=precio_final,
                fecha_vencimiento=s["fecha_vencimiento"],
                link_pago=link,
            )
            print(f"[SUPERADMIN] ✅ Email cobro enviado a {s['email_contacto']}")
        except Exception as e:
            print(f"[SUPERADMIN] Error email cobro: {e}")
        return {"ok": True, "link_pago": link}
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════

@router.get("/usuarios")
def listar_usuarios():
    users = get_users()
    return [
        {
            "username":     u,
            "role":         data.get("role"),
            "professional": data.get("professional"),
            "active":       data.get("active", True),
        }
        for u, data in users.items()
        if u != "public_web"
    ]


@router.patch("/usuarios/{username}/active")
def toggle_usuario(username: str, data: dict):
    users = get_users()
    if username not in users:
        raise HTTPException(404, "Usuario no encontrado")
    users[username]["active"] = data.get("active", True)
    save_user(username, users[username])
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════

@router.get("/audit")
def audit_log(
    rut:     str = Query(None),
    usuario: str = Query(None),
    limite:  int = Query(100, le=500),
):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if rut:
                cur.execute("SELECT * FROM audit_log WHERE rut_paciente = %s ORDER BY created_at DESC LIMIT %s", (rut, limite))
            elif usuario:
                cur.execute("SELECT * FROM audit_log WHERE usuario = %s ORDER BY created_at DESC LIMIT %s", (usuario, limite))
            else:
                cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT %s", (limite,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# PROFESIONALES
# ══════════════════════════════════════════════════════════════

@router.get("/profesionales")
def listar_profesionales():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, rut, specialty, active, created_at FROM profesionales ORDER BY name")
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _generar_link_pago(centro_id: str, monto: int, email: str) -> str:
    from modules.pagos.flow_client import crear_pago
    mes    = date.today().strftime("%Y-%m")
    result = crear_pago(
        id_pago=f"SUB-{centro_id}-{mes}",
        amount=monto,
        subject=f"Suscripción sistema clínico ICA — {mes}",
        email=email,
        url_confirmation=f"{BACKEND_URL}/api/suscripciones/webhook/pago",
        url_return=f"{FRONTEND_URL}/suscripciones",
        optional_data={"centro_id": centro_id},
    )
    return f"{result['url']}?token={result['token']}"
    

"""
modules/superadmin/superadmin_router.py
Endpoints exclusivos del superadministrador de la plataforma.
Protegidos por API key — no por usuarios de BD.
"""
from __future__ import annotations

import os, json
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
    get_centro,
    save_centro,
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

    # Si es plan centro → grabar en tabla centros + provisionar
    if plan == "centro":
        try:
            save_centro({
                "id":             centro_id,
                "nombre":         data.get("nombre_centro", centro_id),
                "email_contacto": data.get("email_contacto", ""),
                "activo":         True,
                "plan":           plan,
                "max_usuarios":   roles,
            })
            print(f"[SUPERADMIN] ✅ Centro '{centro_id}' grabado en tabla centros")
        except Exception as e:
            print(f"[SUPERADMIN] Error grabando centro: {e}")

        try:
            from modules.superadmin.provisioning_service import provisionar_centro
            provisionar_centro(centro_id)
            print(f"[SUPERADMIN] ✅ Infraestructura provisionada para centro {centro_id}")
        except Exception as e:
            print(f"[SUPERADMIN] ⚠️ Provisioning centro error: {e}")

    # Si es externo con subdominio → provisionar
    elif plan not in ("externo_base", ""):
        try:
            from modules.superadmin.provisioning_service import provisionar_externo_completo
            provisionar_externo_completo(centro_id)
            print(f"[SUPERADMIN] ✅ Infraestructura provisionada para {centro_id}")
        except Exception as e:
            print(f"[SUPERADMIN] ⚠️ Provisioning error: {e}")

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

    plan = s.get("plan", "")

    # Desprovisionar según plan — centro_id ES el subdominio
    if plan == "centro":
        try:
            from modules.superadmin.deprovisioning_service import desprovisionar_centro
            desprovisionar_centro(centro_id)
            print(f"[SUPERADMIN] ✅ Infraestructura centro eliminada para {centro_id}")
        except Exception as e:
            print(f"[SUPERADMIN] ⚠️ Deprovisioning centro error: {e}")

    elif plan not in ("externo_base", ""):
        # externo_completo, dermatologia, reumatologia — todos tienen subdominio
        try:
            from modules.superadmin.deprovisioning_service import desprovisionar_externo_completo
            desprovisionar_externo_completo(centro_id)
            print(f"[SUPERADMIN] ✅ Infraestructura externo eliminada para {centro_id}")
        except Exception as e:
            print(f"[SUPERADMIN] ⚠️ Deprovisioning externo error: {e}")

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM suscripciones WHERE centro_id = %s", (centro_id,))
            conn.commit()

    return {"ok": True, "deleted": centro_id}


@router.post("/suscripciones/{centro_id}/activar")
def activar_suscripcion(centro_id: str):
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")
    nueva_fecha = (date.today() + timedelta(days=30)).isoformat()
    update_suscripcion(centro_id, {
        "estado":            "activo",
        "fecha_vencimiento": nueva_fecha,
    })
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
    s = get_suscripcion(centro_id)
    if not s:
        raise HTTPException(404, "Suscripción no encontrada")

    if "roles" in data and s.get("plan") == "centro":
        roles    = data["roles"]
        desc_pct = data.get("descuento_pct", s.get("descuento_pct", 0))
        precios  = calcular_precio_centro(roles, desc_pct)
        data["precio_base"]  = precios["precio_base"]
        data["precio_final"] = precios["precio_final"]
        try:
            centro = get_centro(centro_id)
            if centro:
                centro["max_usuarios"] = roles
                save_centro(centro)
        except Exception as e:
            print(f"[SUPERADMIN] Error actualizando centro: {e}")
    elif "descuento_pct" in data and "roles" not in data:
        desc_pct = data["descuento_pct"]
        data["precio_final"] = int(s["precio_base"] * (1 - desc_pct / 100))

    if "roles" in data and isinstance(data["roles"], dict):
        data["roles"] = json.dumps(data["roles"])

    update_suscripcion(centro_id, data)

    campos_relevantes = {"roles", "precio_final", "fecha_vencimiento", "descuento_pct", "estado"}
    if campos_relevantes & set(data.keys()):
        try:
            s_act  = get_suscripcion(centro_id)
            email  = s_act.get("email_contacto") or s.get("email_contacto")
            if email:
                link = ""
                try:
                    link = _generar_link_pago(centro_id, s_act.get("precio_final", 0), email)
                except Exception as e:
                    print(f"[SUPERADMIN] Error generando link en edición: {e}")
                from notifications.email_suscripciones import enviar_recordatorio_renovacion
                enviar_recordatorio_renovacion(
                    email_contacto=email,
                    nombre_centro=s_act.get("nombre_centro", centro_id),
                    monto=s_act.get("precio_final", 0),
                    fecha_vencimiento=s_act.get("fecha_vencimiento", ""),
                    link_pago=link or "Contacte a contacto@icarticular.cl",
                )
                print(f"[SUPERADMIN] ✅ Email actualización enviado a {email}")
        except Exception as e:
            print(f"[SUPERADMIN] Error email edición: {e}")

    return {"ok": True}


@router.post("/suscripciones/{centro_id}/cobrar")
def cobrar_suscripcion(centro_id: str):
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
        link = _generar_link_pago(centro_id, precio_final, s["email_contacto"])
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
# EXTERNOS — envío de credenciales
# ══════════════════════════════════════════════════════════════

@router.post("/externos/{centro_id}/enviar-credenciales")
def enviar_credenciales_externo(centro_id: str, data: dict):
    try:
        from notifications.email_suscripciones import enviar_credenciales_externo
        ok = enviar_credenciales_externo(
            email_contacto=data["email_contacto"],
            nombre=data["nombre"],
            username=data["username"],
            password_temp=data["password_temp"],
            plan=data["plan"],
        )
        if not ok:
            raise HTTPException(500, "Error enviando email")
        print(f"[SUPERADMIN] ✅ Credenciales externo enviadas a {data['email_contacto']}")
        return {"ok": True}
    except HTTPException:
        raise
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
    import time
    mes     = date.today().strftime("%Y-%m")
    id_pago = f"SUB-{centro_id}-{mes}-{int(time.time()) % 10000}"
    result  = crear_pago(
        id_pago=id_pago,
        amount=monto,
        subject=f"Suscripción sistema clínico ICA — {mes}",
        email=email,
        url_confirmation=f"{BACKEND_URL}/api/suscripciones/webhook/pago",
        url_return=f"{BACKEND_URL}/api/suscripciones/retorno",
        optional_data={"centro_id": centro_id},
    )
    return f"{result['url']}?token={result['token']}"

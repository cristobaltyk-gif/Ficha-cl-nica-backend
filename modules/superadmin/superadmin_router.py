"""
modules/superadmin/superadmin_router.py
Endpoints exclusivos del superadministrador de la plataforma.
Protegidos por API key — no por usuarios de BD.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from auth.superadmin_auth import require_superadmin
from db.supabase_client import (
    _get_conn,
    get_all_suscripciones,
    update_suscripcion,
    get_users,
    save_user,
)

router = APIRouter(
    prefix="/api/superadmin",
    tags=["Superadmin"],
    dependencies=[Depends(require_superadmin)]
)


# ══════════════════════════════════════════════════════════════
# DASHBOARD — KPIs globales
# ══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard():
    suscripciones = get_all_suscripciones()
    activas  = [s for s in suscripciones if s.get("estado") == "activo"]
    vencidas = [s for s in suscripciones if s.get("estado") == "vencido"]
    mrr      = sum(s.get("precio_final", 0) for s in activas)

    # Total usuarios activos
    users = get_users()
    usuarios_activos = sum(1 for u in users.values() if u.get("active", True))

    # Total profesionales
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM profesionales WHERE active = TRUE")
            total_profesionales = cur.fetchone()["total"]

    return {
        "centros_activos":    len(activas),
        "centros_vencidos":   len(vencidas),
        "mrr":                mrr,
        "usuarios_activos":   usuarios_activos,
        "total_profesionales": total_profesionales,
    }


# ══════════════════════════════════════════════════════════════
# SUSCRIPCIONES
# ══════════════════════════════════════════════════════════════

@router.get("/suscripciones")
def listar_suscripciones():
    return get_all_suscripciones()


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


# ══════════════════════════════════════════════════════════════
# USUARIOS — vista global
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
# AUDIT LOG — quién accedió a qué
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
                cur.execute("""
                    SELECT * FROM audit_log
                    WHERE rut_paciente = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (rut, limite))
            elif usuario:
                cur.execute("""
                    SELECT * FROM audit_log
                    WHERE usuario = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (usuario, limite))
            else:
                cur.execute("""
                    SELECT * FROM audit_log
                    ORDER BY created_at DESC LIMIT %s
                """, (limite,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
# PROFESIONALES — vista global
# ══════════════════════════════════════════════════════════════

@router.get("/profesionales")
def listar_profesionales():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, rut, specialty, active, created_at
                FROM profesionales
                ORDER BY name
            """)
            rows = cur.fetchall()
    return [dict(r) for r in rows]
  

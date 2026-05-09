"""
modules/superadmin/centros_router.py
Gestión de centros clínicos.

Dos routers:
- router         → prefijo /api/superadmin/centros — requiere X-Superadmin-Key
- router_interno → prefijo /api/centros            — requiere X-Internal-User (solo lectura)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional

from auth.superadmin_auth import require_superadmin
from auth.internal_auth import require_internal_auth
from db.supabase_client import (
    get_centros, get_centro, save_centro,
    delete_centro, get_usuarios_centro
)

# ── Router superadmin (escritura) ──────────────────────────────
router = APIRouter(
    prefix="/api/superadmin/centros",
    tags=["Superadmin - Centros"],
    dependencies=[Depends(require_superadmin)]
)

# ── Router interno (solo lectura, X-Internal-User) ─────────────
router_interno = APIRouter(
    prefix="/api/centros",
    tags=["Centros - Interno"],
    dependencies=[Depends(require_internal_auth)]
)


class CrearCentroRequest(BaseModel):
    id:              str
    nombre:          str
    email_contacto:  str
    plan:            str = "centro"
    max_usuarios:    Dict[str, int] = {}


class ActualizarCentroRequest(BaseModel):
    nombre:         Optional[str] = None
    email_contacto: Optional[str] = None
    activo:         Optional[bool] = None
    max_usuarios:   Optional[Dict[str, int]] = None


# ══════════════════════════════════════════════════════════════
# SUPERADMIN — escritura completa
# ══════════════════════════════════════════════════════════════

@router.get("")
def listar_centros():
    centros = get_centros()
    return [{ **c, "total_usuarios": len(get_usuarios_centro(c["id"])) } for c in centros]


@router.get("/{centro_id}")
def detalle_centro(centro_id: str):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")
    return { **centro, "usuarios": get_usuarios_centro(centro_id) }


@router.post("")
def crear_centro(data: CrearCentroRequest):
    if get_centro(data.id):
        raise HTTPException(409, f"Centro '{data.id}' ya existe")
    save_centro({
        "id": data.id, "nombre": data.nombre,
        "email_contacto": data.email_contacto, "activo": True,
        "plan": data.plan, "max_usuarios": data.max_usuarios,
    })
    return {"ok": True, "id": data.id}


@router.patch("/{centro_id}")
def actualizar_centro(centro_id: str, data: ActualizarCentroRequest):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")
    centro.update(data.dict(exclude_none=True))
    save_centro(centro)
    return {"ok": True}


@router.delete("/{centro_id}")
def borrar_centro(centro_id: str):
    if not get_centro(centro_id):
        raise HTTPException(404, "Centro no encontrado")
    delete_centro(centro_id)
    return {"ok": True, "deleted": centro_id}


@router.get("/{centro_id}/usuarios")
def usuarios_centro(centro_id: str):
    if not get_centro(centro_id):
        raise HTTPException(404, "Centro no encontrado")
    return get_usuarios_centro(centro_id)


# ══════════════════════════════════════════════════════════════
# INTERNO — solo lectura capacidad (X-Internal-User)
# ══════════════════════════════════════════════════════════════

@router_interno.get("/{centro_id}/capacidad")
def capacidad_centro(centro_id: str):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")
    max_u    = centro.get("max_usuarios") or {}
    usuarios = get_usuarios_centro(centro_id)
    conteo   = {}
    for u in usuarios:
        rol = (u.get("role") or {}).get("name", "otro")
        conteo[rol] = conteo.get(rol, 0) + 1
    capacidad = {
        rol: {
            "maximo":     maximo,
            "actual":     conteo.get(rol, 0),
            "disponible": maximo - conteo.get(rol, 0)
        }
        for rol, maximo in max_u.items()
    }
    return {
        "centro_id":      centro_id,
        "nombre":         centro["nombre"],
        "capacidad":      capacidad,
        "total_usuarios": len(usuarios)
    }

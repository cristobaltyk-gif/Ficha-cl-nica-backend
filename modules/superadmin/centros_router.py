"""
modules/superadmin/centros_router.py
Gestión de centros clínicos — solo superadmin.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional

from auth.superadmin_auth import require_superadmin
from db.supabase_client import (
    get_centros, get_centro, save_centro,
    delete_centro, get_usuarios_centro
)

router = APIRouter(
    prefix="/api/superadmin/centros",
    tags=["Superadmin - Centros"],
    dependencies=[Depends(require_superadmin)]
)

PRECIOS_ROL = {
    "medico":     30000,
    "kine":       25000,
    "psicologo":  30000,
    "secretaria": 20000,
    "admin":      20000,
}


class CrearCentroRequest(BaseModel):
    id:              str   # scope del centro ej: "ica", "traumamaule"
    nombre:          str
    email_contacto:  str
    plan:            str = "centro"
    max_usuarios:    Dict[str, int] = {}  # {"medico": 2, "kine": 1}


class ActualizarCentroRequest(BaseModel):
    nombre:         Optional[str] = None
    email_contacto: Optional[str] = None
    activo:         Optional[bool] = None
    max_usuarios:   Optional[Dict[str, int]] = None


# ══════════════════════════════════════════════════════════════
# LISTAR
# ══════════════════════════════════════════════════════════════

@router.get("")
def listar_centros():
    centros = get_centros()
    # Enriquecer con conteo de usuarios y precio
    result = []
    for c in centros:
        usuarios   = get_usuarios_centro(c["id"])
        max_u      = c.get("max_usuarios") or {}
        precio_base = sum(
            PRECIOS_ROL.get(rol, 0) * qty
            for rol, qty in max_u.items()
        )
        result.append({
            **c,
            "total_usuarios": len(usuarios),
            "precio_base":    precio_base,
        })
    return result


# ══════════════════════════════════════════════════════════════
# DETALLE
# ══════════════════════════════════════════════════════════════

@router.get("/{centro_id}")
def detalle_centro(centro_id: str):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")
    usuarios = get_usuarios_centro(centro_id)
    return { **centro, "usuarios": usuarios }


# ══════════════════════════════════════════════════════════════
# CREAR
# ══════════════════════════════════════════════════════════════

@router.post("")
def crear_centro(data: CrearCentroRequest):
    if get_centro(data.id):
        raise HTTPException(409, f"Centro '{data.id}' ya existe")

    save_centro({
        "id":             data.id,
        "nombre":         data.nombre,
        "email_contacto": data.email_contacto,
        "activo":         True,
        "plan":           data.plan,
        "max_usuarios":   data.max_usuarios,
    })
    return {"ok": True, "id": data.id}


# ══════════════════════════════════════════════════════════════
# ACTUALIZAR
# ══════════════════════════════════════════════════════════════

@router.patch("/{centro_id}")
def actualizar_centro(centro_id: str, data: ActualizarCentroRequest):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")

    updates = data.dict(exclude_none=True)
    centro.update(updates)
    save_centro(centro)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# BORRAR
# ══════════════════════════════════════════════════════════════

@router.delete("/{centro_id}")
def borrar_centro(centro_id: str):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")

    delete_centro(centro_id)
    return {"ok": True, "deleted": centro_id}


# ══════════════════════════════════════════════════════════════
# USUARIOS DEL CENTRO
# ══════════════════════════════════════════════════════════════

@router.get("/{centro_id}/usuarios")
def usuarios_centro(centro_id: str):
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")
    return get_usuarios_centro(centro_id)


@router.get("/{centro_id}/capacidad")
def capacidad_centro(centro_id: str):
    """Muestra cuántos usuarios tiene vs cuántos puede tener."""
    centro = get_centro(centro_id)
    if not centro:
        raise HTTPException(404, "Centro no encontrado")

    max_u    = centro.get("max_usuarios") or {}
    usuarios = get_usuarios_centro(centro_id)

    # Contar por rol
    conteo = {}
    for u in usuarios:
        rol = (u.get("role") or {}).get("name", "otro")
        conteo[rol] = conteo.get(rol, 0) + 1

    capacidad = {}
    for rol, maximo in max_u.items():
        capacidad[rol] = {
            "maximo":    maximo,
            "actual":    conteo.get(rol, 0),
            "disponible":maximo - conteo.get(rol, 0),
        }

    return {
        "centro_id": centro_id,
        "nombre":    centro["nombre"],
        "capacidad": capacidad,
        "total_usuarios": len(usuarios),
    }

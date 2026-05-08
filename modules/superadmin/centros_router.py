"""
modules/superadmin/centros_router.py
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from auth.superadmin_auth import require_superadmin
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_usuarios_centro, get_suscripcion

router = APIRouter(
    prefix="/api/superadmin/centros",
    tags=["Superadmin - Centros"],
    dependencies=[Depends(require_superadmin)]
)


@router.get("/{centro_id}/capacidad", dependencies=[])
def capacidad_centro(centro_id: str, auth=Depends(require_internal_auth)):
    """Lee capacidad desde suscripciones — sin tabla centros."""
    s = get_suscripcion(centro_id)
    if not s:
        return {"centro_id": centro_id, "capacidad": {}, "total_usuarios": 0}

    import json
    roles = s.get("roles") or {}
    if isinstance(roles, str):
        roles = json.loads(roles)

    usuarios = get_usuarios_centro(centro_id)
    conteo   = {}
    for u in usuarios:
        rol = (u.get("role") or {}).get("name", "otro")
        conteo[rol] = conteo.get(rol, 0) + 1

    capacidad = {
        rol: {
            "maximo":     maximo,
            "actual":     conteo.get(rol, 0),
            "disponible": maximo - conteo.get(rol, 0),
        }
        for rol, maximo in roles.items()
    }

    return {
        "centro_id":      centro_id,
        "nombre":         s.get("nombre_centro", ""),
        "capacidad":      capacidad,
        "total_usuarios": len(usuarios),
    }
    

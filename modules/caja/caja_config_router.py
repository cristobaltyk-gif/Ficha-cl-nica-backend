"""
modules/caja/caja_config_router.py
"""
from __future__ import annotations
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_caja_config, save_caja_config

router = APIRouter(prefix="/api/caja/admin/config", tags=["Caja Config"])


def _require_admin(user: dict) -> None:
    if user.get("role", {}).get("name", "") not in ("admin", "secretaria"):
        raise HTTPException(status_code=403, detail="Solo admin o secretaria")


class ValoresGlobalesPayload(BaseModel):
    valores: Dict[str, int]

class ValoresProfesionalPayload(BaseModel):
    professional_id: str
    valores: Dict[str, int]


@router.get("")
def get_config_completa(user=Depends(require_internal_auth)):
    _require_admin(user)
    return get_caja_config()


@router.get("/profesional/{professional_id}")
def get_config_profesional(professional_id: str, user=Depends(require_internal_auth)):
    _require_admin(user)
    config = get_caja_config()
    por_prof = config.get("por_profesional", {})
    if professional_id not in por_prof:
        raise HTTPException(status_code=404, detail="Profesional sin config específica")
    return {"professional_id": professional_id, "valores": por_prof[professional_id],
            "globales": {k: v for k, v in config.items() if k != "por_profesional"}}


@router.put("/globales")
def update_globales(payload: ValoresGlobalesPayload, user=Depends(require_internal_auth)):
    _require_admin(user)
    if any(v < 0 for v in payload.valores.values()):
        raise HTTPException(status_code=400, detail="Los valores no pueden ser negativos")
    config = get_caja_config()
    config.update(payload.valores)
    save_caja_config(config)
    return {"ok": True}


@router.put("/profesional")
def update_profesional(payload: ValoresProfesionalPayload, user=Depends(require_internal_auth)):
    _require_admin(user)
    if any(v < 0 for v in payload.valores.values()):
        raise HTTPException(status_code=400, detail="Los valores no pueden ser negativos")
    config = get_caja_config()
    config.setdefault("por_profesional", {})[payload.professional_id] = payload.valores
    save_caja_config(config)
    return {"ok": True, "professional_id": payload.professional_id, "valores": payload.valores}


@router.patch("/profesional/{professional_id}/{tipo}")
def patch_tipo_profesional(professional_id: str, tipo: str, valor: int, user=Depends(require_internal_auth)):
    _require_admin(user)
    if valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")
    config = get_caja_config()
    config.setdefault("por_profesional", {}).setdefault(professional_id, {})[tipo] = valor
    save_caja_config(config)
    return {"ok": True}


@router.patch("/globales/{tipo}")
def patch_tipo_global(tipo: str, valor: int, user=Depends(require_internal_auth)):
    _require_admin(user)
    if valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")
    config = get_caja_config()
    config[tipo] = valor
    save_caja_config(config)
    return {"ok": True}


@router.delete("/profesional/{professional_id}/{tipo}")
def delete_tipo_profesional(professional_id: str, tipo: str, user=Depends(require_internal_auth)):
    _require_admin(user)
    config = get_caja_config()
    por_prof = config.get("por_profesional", {})
    if professional_id not in por_prof:
        raise HTTPException(status_code=404, detail="Profesional sin config específica")
    if tipo not in por_prof[professional_id]:
        raise HTTPException(status_code=404, detail=f"Tipo '{tipo}' no existe")
    del config["por_profesional"][professional_id][tipo]
    save_caja_config(config)
    return {"ok": True}


@router.delete("/profesional/{professional_id}")
def delete_config_profesional(professional_id: str, user=Depends(require_internal_auth)):
    _require_admin(user)
    config = get_caja_config()
    if professional_id not in config.get("por_profesional", {}):
        raise HTTPException(status_code=404, detail="Profesional sin config específica")
    del config["por_profesional"][professional_id]
    save_caja_config(config)
    return {"ok": True}
    

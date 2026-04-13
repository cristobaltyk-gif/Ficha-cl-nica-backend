"""
modules/caja/caja_config_router.py

Admin puede leer y modificar valores de caja_config.json:
- Valores globales (fallback)
- Valores por profesional
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Optional, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.internal_auth import require_internal_auth

router = APIRouter(prefix="/api/caja/admin/config", tags=["Caja Config"])

CONFIG_PATH = Path(__file__).parent / "caja_config.json"
LOCK        = Lock()


# ============================================================
# HELPERS
# ============================================================

def _load() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _require_admin(user: dict) -> None:
    role = user.get("role", {}).get("name", "")
    if role not in ("admin", "secretaria"):
        raise HTTPException(status_code=403, detail="Solo admin o secretaria pueden modificar valores")


# ============================================================
# SCHEMAS
# ============================================================

class ValoresGlobalesPayload(BaseModel):
    valores: Dict[str, int]  # {"particular": 45000, "sobrecupo": 45000, ...}


class ValoresProfesionalPayload(BaseModel):
    professional_id: str
    valores: Dict[str, int]  # {"particular": 25000, "paquete_10": 200000, ...}


class EliminarTipoProfesionalPayload(BaseModel):
    professional_id: str
    tipo: str


# ============================================================
# GET — leer config completa
# ============================================================

@router.get("")
def get_config_completa(user=Depends(require_internal_auth)):
    _require_admin(user)
    return _load()


# ============================================================
# GET — leer valores de un profesional
# ============================================================

@router.get("/profesional/{professional_id}")
def get_config_profesional(professional_id: str, user=Depends(require_internal_auth)):
    _require_admin(user)
    config   = _load()
    por_prof = config.get("por_profesional", {})
    if professional_id not in por_prof:
        raise HTTPException(status_code=404, detail="Profesional sin config específica")
    return {
        "professional_id": professional_id,
        "valores":         por_prof[professional_id],
        "globales":        {k: v for k, v in config.items() if k != "por_profesional"},
    }


# ============================================================
# PUT — actualizar valores globales (fallback)
# ============================================================

@router.put("/globales")
def update_globales(payload: ValoresGlobalesPayload, user=Depends(require_internal_auth)):
    _require_admin(user)

    if any(v < 0 for v in payload.valores.values()):
        raise HTTPException(status_code=400, detail="Los valores no pueden ser negativos")

    with LOCK:
        config = _load()
        for tipo, valor in payload.valores.items():
            config[tipo] = valor
        _save(config)

    return {"ok": True, "globales": {k: v for k, v in config.items() if k != "por_profesional"}}


# ============================================================
# PUT — actualizar valores de un profesional
# ============================================================

@router.put("/profesional")
def update_profesional(payload: ValoresProfesionalPayload, user=Depends(require_internal_auth)):
    _require_admin(user)

    if any(v < 0 for v in payload.valores.values()):
        raise HTTPException(status_code=400, detail="Los valores no pueden ser negativos")

    with LOCK:
        config = _load()
        config.setdefault("por_profesional", {})[payload.professional_id] = payload.valores
        _save(config)

    return {
        "ok":             True,
        "professional_id": payload.professional_id,
        "valores":         payload.valores,
    }


# ============================================================
# PATCH — actualizar un solo tipo de un profesional
# ============================================================

@router.patch("/profesional/{professional_id}/{tipo}")
def patch_tipo_profesional(
    professional_id: str,
    tipo:            str,
    valor:           int,
    user=Depends(require_internal_auth)
):
    _require_admin(user)

    if valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")

    with LOCK:
        config = _load()
        config.setdefault("por_profesional", {}).setdefault(professional_id, {})[tipo] = valor
        _save(config)

    return {"ok": True, "professional_id": professional_id, "tipo": tipo, "valor": valor}


# ============================================================
# PATCH — actualizar un tipo global
# ============================================================

@router.patch("/globales/{tipo}")
def patch_tipo_global(tipo: str, valor: int, user=Depends(require_internal_auth)):
    _require_admin(user)

    if valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")

    with LOCK:
        config = _load()
        config[tipo] = valor
        _save(config)

    return {"ok": True, "tipo": tipo, "valor": valor}


# ============================================================
# DELETE — eliminar tipo de un profesional
# ============================================================

@router.delete("/profesional/{professional_id}/{tipo}")
def delete_tipo_profesional(
    professional_id: str,
    tipo:            str,
    user=Depends(require_internal_auth)
):
    _require_admin(user)

    with LOCK:
        config   = _load()
        por_prof = config.get("por_profesional", {})

        if professional_id not in por_prof:
            raise HTTPException(status_code=404, detail="Profesional sin config específica")
        if tipo not in por_prof[professional_id]:
            raise HTTPException(status_code=404, detail=f"Tipo '{tipo}' no existe para este profesional")

        del config["por_profesional"][professional_id][tipo]
        _save(config)

    return {"ok": True, "professional_id": professional_id, "tipo_eliminado": tipo}


# ============================================================
# DELETE — eliminar config completa de un profesional
# ============================================================

@router.delete("/profesional/{professional_id}")
def delete_config_profesional(professional_id: str, user=Depends(require_internal_auth)):
    _require_admin(user)

    with LOCK:
        config   = _load()
        por_prof = config.get("por_profesional", {})

        if professional_id not in por_prof:
            raise HTTPException(status_code=404, detail="Profesional sin config específica")

        del config["por_profesional"][professional_id]
        _save(config)

    return {"ok": True, "professional_id": professional_id, "eliminado": True}
  

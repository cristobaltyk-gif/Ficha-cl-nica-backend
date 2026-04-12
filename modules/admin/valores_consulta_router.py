"""
modules/admin/valores_consulta_router.py

Administra el valor de consulta por profesional.
Graba en /data/valores_consulta.json separado de professionals.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.internal_auth import require_internal_auth

router = APIRouter(prefix="/api/admin/valores-consulta", tags=["Admin"])

VALORES_PATH        = Path("/data/valores_consulta.json")
PROFESSIONALS_PATH  = Path("/data/professionals.json")
LOCK                = Lock()
DEFAULT_VALOR       = 50000


# ============================================================
# HELPERS
# ============================================================

def _load_valores() -> dict:
    if not VALORES_PATH.exists():
        return {}
    with open(VALORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_valores(data: dict) -> None:
    VALORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VALORES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_professionals() -> dict:
    if not PROFESSIONALS_PATH.exists():
        return {}
    with open(PROFESSIONALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_valor_consulta(professional_id: str) -> int:
    """Función pública para otros routers."""
    valores = _load_valores()
    return valores.get(professional_id, DEFAULT_VALOR)


# ============================================================
# SCHEMAS
# ============================================================

class ValorConsultaPayload(BaseModel):
    valor: int


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("")
def listar_valores(user=Depends(require_internal_auth)):
    """Lista todos los profesionales con su valor de consulta."""
    profesionales = _load_professionals()
    valores       = _load_valores()

    result = []
    for pid, prof in profesionales.items():
        if not prof.get("active", True):
            continue
        result.append({
            "id":             pid,
            "name":           prof.get("name", pid),
            "specialty":      prof.get("specialty", ""),
            "valor_consulta": valores.get(pid, DEFAULT_VALOR),
        })

    return result


@router.get("/{professional_id}")
def get_valor(professional_id: str, user=Depends(require_internal_auth)):
    profesionales = _load_professionals()
    if professional_id not in profesionales:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    prof  = profesionales[professional_id]
    valor = get_valor_consulta(professional_id)

    return {
        "id":             professional_id,
        "name":           prof.get("name", professional_id),
        "valor_consulta": valor,
    }


@router.put("/{professional_id}")
def set_valor(
    professional_id: str,
    payload: ValorConsultaPayload,
    user=Depends(require_internal_auth)
):
    # Solo secretaria o admin puede modificar
    role_name = user.get("role", {}).get("name", "")
    if role_name not in ("secretaria", "admin"):
        raise HTTPException(status_code=403, detail="Sin permisos para modificar valores")

    profesionales = _load_professionals()
    if professional_id not in profesionales:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    if payload.valor < 0:
        raise HTTPException(status_code=400, detail="El valor no puede ser negativo")

    with LOCK:
        valores = _load_valores()
        valores[professional_id] = payload.valor
        _save_valores(valores)

    return {
        "ok":             True,
        "id":             professional_id,
        "valor_consulta": payload.valor,
    }


@router.post("/inicializar")
def inicializar_valores(user=Depends(require_internal_auth)):
    """
    Inicializa valores_consulta.json con todos los profesionales activos
    que aún no tienen valor asignado. Útil al agregar nuevos profesionales.
    """
    role_name = user.get("role", {}).get("name", "")
    if role_name not in ("secretaria", "admin"):
        raise HTTPException(status_code=403, detail="Sin permisos")

    profesionales = _load_professionals()

    with LOCK:
        valores    = _load_valores()
        agregados  = []

        for pid, prof in profesionales.items():
            if pid not in valores and prof.get("active", True):
                valores[pid] = DEFAULT_VALOR
                agregados.append(pid)

        _save_valores(valores)

    return {"ok": True, "agregados": agregados, "total": len(valores)}
      

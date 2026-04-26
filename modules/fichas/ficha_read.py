from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, search_pacientes, log_acceso

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Read"],
    dependencies=[Depends(require_internal_auth)]
)


@router.get("/search")
def search_fichas(
    q: str = Query(..., min_length=2),
    request: Request = None,
    user=Depends(require_internal_auth)
):
    results = search_pacientes(q)
    log_acceso(
        usuario=user["usuario"],
        accion="buscar_fichas",
        ip=request.client.host if request else None,
        detalle=f"query: {q} — {len(results)} resultados"
    )
    return {"total": len(results), "results": results}


@router.get("/{rut}")
def get_ficha_administrativa(
    rut: str,
    request: Request = None,
    user=Depends(require_internal_auth)
) -> Dict[str, Any]:
    ficha = get_paciente(rut)
    if not ficha:
        raise HTTPException(404, "Ficha no encontrada")
    log_acceso(
        usuario=user["usuario"],
        accion="ver_ficha_administrativa",
        rut_paciente=rut,
        ip=request.client.host if request else None,
    )
    return ficha
    

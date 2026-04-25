from __future__ import annotations

from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, search_pacientes

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Read"],
    dependencies=[Depends(require_internal_auth)]
)


@router.get("/search")
def search_fichas(q: str = Query(..., min_length=2)):
    results = search_pacientes(q)
    return {"total": len(results), "results": results}


@router.get("/{rut}")
def get_ficha_administrativa(rut: str) -> Dict[str, Any]:
    ficha = get_paciente(rut)
    if not ficha:
        raise HTTPException(404, "Ficha no encontrada")
    return ficha

from __future__ import annotations
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, search_pacientes, log_acceso, get_eventos

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Read"],
    dependencies=[Depends(require_internal_auth)]
)


def _profesional_atendio_paciente(profesional_id: str, rut: str) -> bool:
    try:
        eventos = get_eventos(rut)
        return any(ev.get("professional_id") == profesional_id for ev in eventos)
    except Exception:
        return False


@router.get("/search")
def search_fichas(
    q: str = Query(..., min_length=2),
    request: Request = None,
    user=Depends(require_internal_auth)
):
    scope       = user.get("role", {}).get("scope", "ica")
    profesional = user.get("professional")

    results = search_pacientes(q)

    if scope == "externo" and profesional:
        results = [
            r for r in results
            if _profesional_atendio_paciente(profesional, r["rut"])
        ]

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
    scope       = user.get("role", {}).get("scope", "ica")
    profesional = user.get("professional")

    ficha = get_paciente(rut)
    if not ficha:
        raise HTTPException(404, "Ficha no encontrada")

    if scope == "externo" and profesional:
        if not _profesional_atendio_paciente(profesional, rut):
            raise HTTPException(status_code=403, detail="No autorizado para ver esta ficha")

    log_acceso(
        usuario=user["usuario"],
        accion="ver_ficha_administrativa",
        rut_paciente=rut,
        ip=request.client.host if request else None,
    )
    return ficha
    

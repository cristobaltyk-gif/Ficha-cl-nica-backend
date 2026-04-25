from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, get_eventos_resumen

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - List"],
    dependencies=[Depends(require_internal_auth)]
)


@router.get("/{rut}")
def list_clinical_events(
    rut: str,
    user=Depends(require_internal_auth)
) -> List[Dict[str, Any]]:

    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="La ficha del paciente no existe")

    return get_eventos_resumen(rut)

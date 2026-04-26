from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, get_eventos, get_eventos_resumen
from core.professionals_store import list_professionals

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Read"],
    dependencies=[Depends(require_internal_auth)]
)


@router.get("/{rut}")
def get_clinical_events(
    rut: str,
    user=Depends(require_internal_auth)
) -> List[Dict[str, Any]]:

    role = user.get("role", {})
    if role.get("name") not in ["medico", "kinesiologia"]:
        raise HTTPException(status_code=403, detail="No autorizado para leer ficha clínica")

    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="La ficha del paciente no existe")

    professionals_list = list_professionals()
    professionals_map  = {p["id"]: p for p in professionals_list}

    eventos = get_eventos(rut)
    for ev in eventos:
        pid = ev.get("professional_id")
        if pid and pid in professionals_map:
            ev["professional_name"] = professionals_map[pid]["name"]
        else:
            ev["professional_name"] = pid or ""

    return eventos
    

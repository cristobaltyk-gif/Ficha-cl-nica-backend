from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, get_eventos, get_eventos_resumen
from core.professionals_store import list_professionals
from db.supabase_client import get_users

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
    if role.get("name") not in ["medico", "psicologo", "kine"]:
        raise HTTPException(status_code=403, detail="No autorizado para leer ficha clínica")

    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="La ficha del paciente no existe")

    scope          = role.get("scope", "ica")
    my_professional = user.get("professional")

    professionals_list = list_professionals()
    professionals_map  = {p["id"]: p for p in professionals_list}

    users = get_users()

    def _prof_scope(pid: str) -> str:
        u = users.get(pid, {})
        return (u.get("role") or {}).get("scope", "ica")

    eventos = get_eventos(rut)

    eventos_filtrados = []
    for ev in eventos:
        pid = ev.get("professional_id")
        prof_scope = _prof_scope(pid) if pid else "ica"

        if scope == "ica":
            if prof_scope != "ica":
                continue
        else:
            if pid != my_professional:
                continue

        if pid and pid in professionals_map:
            ev["professional_name"] = professionals_map[pid]["name"]
        else:
            ev["professional_name"] = pid or ""

        eventos_filtrados.append(ev)

    return eventos_filtrados

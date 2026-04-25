from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, update_paciente

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Update"],
    dependencies=[Depends(require_internal_auth)]
)

CAMPOS_PERMITIDOS = [
    "nombre", "apellido_paterno", "apellido_materno",
    "fecha_nacimiento", "sexo", "direccion",
    "telefono", "email", "prevision"
]


@router.put("/{rut}")
def update_ficha_administrativa(
    rut: str,
    data: Dict[str, Any],
    auth=Depends(require_internal_auth)
):
    ficha = get_paciente(rut)
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha administrativa no existe")

    for field in CAMPOS_PERMITIDOS:
        if field in data:
            ficha[field] = data[field]

    update_paciente(rut, ficha)
    return {"status": "ok", "rut": rut}

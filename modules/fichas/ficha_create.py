from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, create_paciente

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Create"],
    dependencies=[Depends(require_internal_auth)]
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("")
def create_ficha_administrativa(data: Dict[str, Any]):
    required = ["rut", "nombre", "apellido_paterno", "fecha_nacimiento"]
    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(
                status_code=400,
                detail=f"Campo obligatorio faltante: {field}"
            )

    rut = data["rut"]

    if get_paciente(rut):
        raise HTTPException(status_code=409, detail="Ficha administrativa ya existe")

    ficha = {
        "rut":              rut,
        "nombre":           data["nombre"],
        "apellido_paterno": data["apellido_paterno"],
        "apellido_materno": data.get("apellido_materno", ""),
        "fecha_nacimiento": data["fecha_nacimiento"],
        "sexo":             data.get("sexo", ""),
        "direccion":        data.get("direccion", ""),
        "telefono":         data.get("telefono", ""),
        "email":            data.get("email", ""),
        "prevision":        data.get("prevision", ""),
    }

    create_paciente(ficha)
    return {"status": "ok", "rut": rut}

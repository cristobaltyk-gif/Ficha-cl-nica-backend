from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from auth.internal_auth import require_internal_auth

# ==================================================
# CONFIGURACIÓN CANÓNICA
# ==================================================

BASE_DATA_PATH = Path("/data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Update"],
    dependencies=[Depends(require_internal_auth)]
)

# ==================================================
# HELPERS
# ==================================================
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def admin_file(rut: str) -> Path:
    return BASE_DATA_PATH / rut / "admin.json"


# ==================================================
# ENDPOINT (SOLO UPDATE)
# ==================================================

@router.put("/{rut}")
def update_ficha_administrativa(
    rut: str,
    data: Dict[str, Any],
    auth=Depends(require_internal_auth)
):
    """
    ACTUALIZA ficha administrativa existente
    SOLO con los campos del formulario.
    ❌ No crea
    ❌ No busca
    ❌ No lista
    """

    file = admin_file(rut)

    if not file.exists():
        raise HTTPException(
            status_code=404,
            detail="Ficha administrativa no existe"
        )

    with LOCK:
        ficha = json.loads(file.read_text(encoding="utf-8"))

        # 🔒 CAMPOS PERMITIDOS (CONTRATO FORMULARIO)
        for field in [
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "fecha_nacimiento",
            "direccion",
            "telefono",
            "email",
            "prevision"
        ]:
            if field in data:
                ficha[field] = data[field]

        ficha["updated_at"] = utc_now()

        file.write_text(
            json.dumps(ficha, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "status": "ok",
        "rut": rut
    }

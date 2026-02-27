from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth


# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Read"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# LEER HISTORIAL COMPLETO
# ===============================

@router.get("/{rut}")
def get_clinical_events(rut: str) -> List[Dict[str, Any]]:
    """
    Devuelve todos los eventos clínicos del paciente,
    ordenados por fecha/hora descendente.
    """

    pdir = patient_dir(rut)

    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail="La ficha del paciente no existe"
        )

    events_dir = pdir / "eventos"

    if not events_dir.exists():
        return []

    eventos = []

    for file in sorted(events_dir.glob("*.json"), reverse=True):
        try:
            contenido = json.loads(file.read_text(encoding="utf-8"))
            eventos.append(contenido)
        except Exception:
            continue

    return eventos

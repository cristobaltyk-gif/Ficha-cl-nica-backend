from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth
from core.professionals_store import list_professionals


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
def get_clinical_events(
    rut: str,
    user=Depends(require_internal_auth)
) -> List[Dict[str, Any]]:
    """
    Devuelve todos los eventos clínicos del paciente,
    ordenados por fecha/hora descendente.

    - Respeta auth interno
    - Resuelve professional_name desde professionals_store
    - NO usa USERS
    """

    # ===============================
    # VALIDAR ROL CLÍNICO
    # ===============================
    role = user.get("role", {})
    if role.get("name") not in ["medico", "kinesiologia"]:
        raise HTTPException(
            status_code=403,
            detail="No autorizado para leer ficha clínica"
        )

    pdir = patient_dir(rut)

    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail="La ficha del paciente no existe"
        )

    events_dir = pdir / "eventos"

    if not events_dir.exists():
        return []

    # ===============================
    # CARGAR PROFESIONALES (FUENTE CLÍNICA)
    # ===============================
    professionals_list = list_professionals()
    professionals_map = {p["id"]: p for p in professionals_list}

    eventos = []

    for file in sorted(events_dir.glob("*.json"), reverse=True):
        try:
            contenido = json.loads(file.read_text(encoding="utf-8"))

            # ===============================
            # Resolver nombre profesional
            # ===============================
            professional_id = contenido.get("professional_id")

            if professional_id and professional_id in professionals_map:
                contenido["professional_name"] = (
                    professionals_map[professional_id]["name"]
                )
            else:
                # Fallback seguro
                contenido["professional_name"] = professional_id or ""

            eventos.append(contenido)

        except Exception:
            continue

    return eventos

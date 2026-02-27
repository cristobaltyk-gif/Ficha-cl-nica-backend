from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth


# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - List"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# LISTAR EVENTOS CLÍNICOS
# ===============================

@router.get("/{rut}")
def list_clinical_events(
    rut: str,
    user=Depends(require_internal_auth)
) -> List[Dict[str, Any]]:
    """
    Lista eventos clínicos de un paciente.
    Devuelve resumen:
    - fecha
    - hora
    - diagnostico
    - professional_name
    - created_at
    """

    with LOCK:
        pdir = patient_dir(rut)

        if not pdir.exists():
            raise HTTPException(
                status_code=404,
                detail="La ficha del paciente no existe"
            )

        events_dir = pdir / "eventos"

        if not events_dir.exists():
            return []

        eventos_resumen = []

        for file in events_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))

                eventos_resumen.append({
                    "fecha": data.get("fecha"),
                    "hora": data.get("hora"),
                    "diagnostico": data.get("diagnostico"),
                    "professional_name": data.get("professional_name"),
                    "created_at": data.get("created_at")
                })

            except Exception:
                continue

        # Ordenar por fecha + hora descendente
        eventos_resumen.sort(
            key=lambda x: f"{x.get('fecha','')} {x.get('hora','')}",
            reverse=True
        )

        return eventos_resumen

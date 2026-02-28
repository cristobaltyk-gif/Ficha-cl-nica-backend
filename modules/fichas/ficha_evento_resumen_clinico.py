from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth


# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")

router = APIRouter(
    prefix="/api/fichas/resumen-clinico",
    tags=["Ficha Clínica - Resumen Clínico"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# ENDPOINT
# ===============================

@router.post("/{rut}")
async def generar_resumen_clinico(
    rut: str,
    user=Depends(require_internal_auth)
):
    """
    Lee TODAS las atenciones clínicas del paciente
    y genera un resumen clínico integral en 1 página
    usando el endpoint GPT oficial.
    """

    pdir = patient_dir(rut)

    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail="La ficha del paciente no existe"
        )

    events_dir = pdir / "eventos"

    if not events_dir.exists():
        return {
            "rut": rut,
            "resumen": "Paciente sin atenciones registradas."
        }

    eventos: List[Dict[str, Any]] = []

    # 🔹 Lee TODOS los JSON
    for file in sorted(events_dir.glob("*.json")):
        try:
            contenido = json.loads(
                file.read_text(encoding="utf-8")
            )
            eventos.append(contenido)
        except Exception:
            continue

    if not eventos:
        return {
            "rut": rut,
            "resumen": "Paciente sin atenciones registradas."
        }

    # ===============================
    # CONSTRUIR HISTORIAL COMPLETO
    # ===============================

    historial_texto = ""

    for ev in eventos:
        historial_texto += f"""
Fecha: {ev.get("fecha", "")}
Hora: {ev.get("hora", "")}
Profesional: {ev.get("professional_name", "")}

Motivo Consulta:
{ev.get("atencion", "")}

Diagnóstico:
{ev.get("diagnostico", "")}

Exámenes:
{ev.get("examenes", "")}

Indicaciones:
{ev.get("indicaciones", "")}

Plan:
{ev.get("receta", "")}

------------------------------------------------------------
"""

    # ===============================
    # LLAMAR A GPT SUMMARY ENDPOINT
    # ===============================

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/gpt/clinical-summary",
            json={"historial": historial_texto},
            headers={
                "X-Internal-User": user["usuario"]
            }
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="Error generando resumen clínico"
        )

    resumen = response.json().get("resumen", "")

    return {
        "rut": rut,
        "resumen": resumen
    }

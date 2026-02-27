from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth
from api.gpt_clinical import ask_gpt_clinical   # ⚠️ usamos tu motor actual


# ===============================
# CONFIG
# ===============================

BASE_DATA_PATH = Path("/data/pacientes")
LOCK = Lock()

router = APIRouter(
    prefix="/api/fichas/evento",
    tags=["Ficha Clínica - Resumen Global"],
    dependencies=[Depends(require_internal_auth)]
)


# ===============================
# HELPERS
# ===============================

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


# ===============================
# RESUMEN GLOBAL CON GPT
# ===============================

@router.post("/resumen-global/{rut}")
def generar_resumen_global(
    rut: str,
    user=Depends(require_internal_auth)
) -> Dict[str, Any]:
    """
    Lee TODOS los eventos del paciente,
    concatena texto clínico
    y pide a GPT un resumen en una plana.
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
            raise HTTPException(
                status_code=404,
                detail="El paciente no tiene atenciones registradas"
            )

        textos: List[str] = []

        for file in sorted(events_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))

                bloque = f"""
Fecha: {data.get("fecha")} {data.get("hora")}
Profesional: {data.get("professional_name")}

Motivo:
{data.get("atencion","")}

Diagnóstico:
{data.get("diagnostico","")}

Plan:
{data.get("receta","")}

Exámenes:
{data.get("examenes","")}

Indicaciones:
{data.get("indicaciones","")}
-----------------------------------------------------
"""
                textos.append(bloque)

            except Exception:
                continue

        if not textos:
            raise HTTPException(
                status_code=404,
                detail="No hay contenido clínico para resumir"
            )

        historial_completo = "\n".join(textos)

    # ===============================
    # PROMPT MÉDICO PROFESIONAL
    # ===============================

    prompt = f"""
Eres un médico especialista.

A continuación tienes el historial clínico completo de un paciente.

Redacta un INFORME CLÍNICO INTEGRADO,
en formato profesional,
máximo una plana,
con lenguaje médico técnico,
ordenado y coherente.

Incluye:
- Resumen evolutivo
- Diagnósticos relevantes
- Procedimientos realizados
- Estado actual del paciente
- Plan general

Historial:

{historial_completo}
"""

    try:
        respuesta = ask_gpt_clinical(prompt)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT: {str(e)}"
        )

    return {
        "status": "ok",
        "rut": rut,
        "resumen": respuesta
    }

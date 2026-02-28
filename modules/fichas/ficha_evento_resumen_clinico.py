from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from auth.internal_auth import require_internal_auth
from api.openai_client import ask_gpt  # 👈 usa tu cliente real OpenAI

BASE_DATA_PATH = Path("/data/pacientes")

router = APIRouter(
    prefix="/api/fichas/resumen-clinico",
    tags=["Ficha Clínica - Resumen Clínico"],
    dependencies=[Depends(require_internal_auth)]
)


def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut


@router.post("/{rut}")
async def generar_resumen_clinico(
    rut: str,
    user=Depends(require_internal_auth)
):
    """
    Lee TODAS las atenciones clínicas del paciente
    y genera un resumen clínico integral en 1 página.
    """

    pdir = patient_dir(rut)

    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail="La ficha del paciente no existe"
        )

    events_dir = pdir / "eventos"

    if not events_dir.exists():
        return {"resumen": "Paciente sin atenciones registradas."}

    eventos = []

    for file in sorted(events_dir.glob("*.json")):
        try:
            contenido = json.loads(file.read_text(encoding="utf-8"))
            eventos.append(contenido)
        except Exception:
            continue

    if not eventos:
        return {"resumen": "Paciente sin atenciones registradas."}

    # ===============================
    # CONSTRUIR CONTEXTO PARA GPT
    # ===============================

    historial_texto = ""

    for ev in eventos:
        historial_texto += f"""
Fecha: {ev.get("fecha")}
Hora: {ev.get("hora")}
Profesional: {ev.get("professional_name")}

Motivo Consulta:
{ev.get("atencion")}

Diagnóstico:
{ev.get("diagnostico")}

Exámenes:
{ev.get("examenes")}

Indicaciones:
{ev.get("indicaciones")}

Plan:
{ev.get("receta")}

----------------------------------------
"""

    prompt = f"""
Eres un traumatólogo experto.

Redacta un resumen clínico integral en máximo una página,
lenguaje médico formal, claro y estructurado.

Incluye:
- Antecedentes relevantes
- Evolución clínica
- Diagnósticos principales
- Estudios realizados
- Conducta actual

No inventes datos.
Usa solo la información entregada.

HISTORIAL DEL PACIENTE:

{historial_texto}
"""

    resumen = await ask_gpt(prompt)

    return {
        "rut": rut,
        "resumen": resumen
    }

from __future__ import annotations

from typing import List, Dict, Any, Optional

import anthropic
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, get_eventos

router = APIRouter(
    prefix="/api/fichas/resumen-clinico",
    tags=["Ficha Clínica - Resumen Clínico"],
    dependencies=[Depends(require_internal_auth)]
)

SYSTEM_PROMPT = (
    "Eres un médico especialista en traumatología. "
    "Redactas resúmenes clínicos formales en tercera persona, "
    "sin markdown, sin encabezados decorativos, en texto continuo."
)

USER_TEMPLATE = """Redacta un resumen clínico integral del paciente basado en su historial.

REGLAS:
- No inventes datos.
- No agregues antecedentes no mencionados.
- No agregues diagnósticos no documentados.
- Lenguaje médico formal.
- Tercera persona.
- Máximo una página.
- Sin markdown ni encabezados decorativos.
- Texto continuo, estructurado clínicamente.

Incluye si corresponde:
- Antecedentes relevantes
- Evolución cronológica
- Diagnósticos principales
- Estudios realizados
- Conducta actual
- Situación funcional

HISTORIAL:
\"\"\"
{historial}
\"\"\"
"""


class ResumenRequest(BaseModel):
    eventos_seleccionados: Optional[List[str]] = None


def _build_historial(eventos: List[Dict[str, Any]]) -> str:
    historial = ""
    for ev in eventos:
        historial += f"""
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
    return historial


@router.get("/{rut}/eventos")
def listar_eventos(rut: str, user=Depends(require_internal_auth)):
    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="Ficha no encontrada")

    eventos = get_eventos(rut)
    return {
        "rut": rut,
        "eventos": [
            {
                "id":               f"{ev.get('fecha', '')}_{ev.get('hora', '')}",
                "fecha":            ev.get("fecha", ""),
                "hora":             ev.get("hora", ""),
                "diagnostico":      ev.get("diagnostico", "Sin diagnóstico"),
                "professional_name": ev.get("professional_name", ""),
            }
            for ev in eventos
        ]
    }


@router.post("/{rut}")
def generar_resumen_clinico(
    rut: str,
    body: ResumenRequest = ResumenRequest(),
    user=Depends(require_internal_auth)
):
    if not get_paciente(rut):
        raise HTTPException(status_code=404, detail="Ficha no encontrada")

    todos_eventos = get_eventos(rut)
    if not todos_eventos:
        return {"rut": rut, "resumen": "Paciente sin atenciones registradas."}

    if body.eventos_seleccionados:
        seleccionados = set(body.eventos_seleccionados)
        eventos = [
            ev for ev in todos_eventos
            if f"{ev.get('fecha', '')}_{ev.get('hora', '')}" in seleccionados
        ]
        if not eventos:
            raise HTTPException(status_code=400, detail="Ningún evento seleccionado válido")
    else:
        eventos = todos_eventos

    historial = _build_historial(eventos)

    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(historial=historial)}]
        )
        return {"rut": rut, "resumen": message.content[0].text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Claude: {str(e)}")

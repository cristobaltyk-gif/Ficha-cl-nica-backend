from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import anthropic
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

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


# ===============================
# SCHEMAS
# ===============================

class ResumenRequest(BaseModel):
    # IDs de eventos seleccionados (fecha_hora). Si vacío, usa todos.
    eventos_seleccionados: Optional[List[str]] = None


# ===============================
# HELPERS
# ===============================

def patient_dir(rut: str) -> Path:
    return BASE_DATA_PATH / rut

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


# ===============================
# GET — lista de eventos del paciente
# ===============================

@router.get("/{rut}/eventos")
def listar_eventos(rut: str, user=Depends(require_internal_auth)):
    pdir = patient_dir(rut)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Ficha no encontrada")

    events_dir = pdir / "eventos"
    if not events_dir.exists():
        return {"rut": rut, "eventos": []}

    eventos = []
    for file in sorted(events_dir.glob("*.json"), reverse=True):
        try:
            ev = json.loads(file.read_text(encoding="utf-8"))
            eventos.append({
                "id":               f"{ev.get('fecha', '')}_{ev.get('hora', '')}",
                "fecha":            ev.get("fecha", ""),
                "hora":             ev.get("hora", ""),
                "diagnostico":      ev.get("diagnostico", "Sin diagnóstico"),
                "professional_name": ev.get("professional_name", ""),
            })
        except Exception:
            continue

    return {"rut": rut, "eventos": eventos}


# ===============================
# POST — generar resumen
# ===============================

@router.post("/{rut}")
def generar_resumen_clinico(
    rut: str,
    body: ResumenRequest = ResumenRequest(),
    user=Depends(require_internal_auth)
):
    pdir = patient_dir(rut)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Ficha no encontrada")

    events_dir = pdir / "eventos"
    if not events_dir.exists():
        return {"rut": rut, "resumen": "Paciente sin atenciones registradas."}

    todos_eventos = []
    for file in sorted(events_dir.glob("*.json")):
        try:
            ev = json.loads(file.read_text(encoding="utf-8"))
            todos_eventos.append(ev)
        except Exception:
            continue

    if not todos_eventos:
        return {"rut": rut, "resumen": "Paciente sin atenciones registradas."}

    # Filtrar si hay selección
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
        resumen = message.content[0].text.strip()
        return {"rut": rut, "resumen": resumen}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Claude: {str(e)}")

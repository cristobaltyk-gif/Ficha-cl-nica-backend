from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.openai_client import client
import traceback

router = APIRouter(prefix="/api/gpt", tags=["GPT Resumen Clínico"])


# =========================
# SCHEMAS
# =========================

class ClinicalSummaryRequest(BaseModel):
    historial: str


class ClinicalSummaryResponse(BaseModel):
    resumen: str


# =========================
# ENDPOINT
# =========================

@router.post(
    "/clinical-summary",
    response_model=ClinicalSummaryResponse
)
def clinical_summary(data: ClinicalSummaryRequest):

    print(">>> [GPT] ENDPOINT /clinical-summary ENTRÓ")

    if not data.historial or not data.historial.strip():
        raise HTTPException(
            status_code=400,
            detail="Historial vacío"
        )

    # =========================
    # PROMPT CLÍNICO LONGITUDINAL
    # =========================

    prompt = f"""
Eres un traumatólogo especialista.

Tu tarea es redactar un RESUMEN CLÍNICO INTEGRAL del paciente
basado en todas sus atenciones históricas.

REGLAS ABSOLUTAS:
- NO inventes datos.
- NO agregues antecedentes no mencionados.
- NO agregues diagnósticos no documentados.
- Usa lenguaje médico formal.
- Redacta en tercera persona.
- Máximo una página.
- Sin markdown.
- Sin encabezados decorativos.
- Texto continuo, estructurado clínicamente.

Debe incluir si corresponde:
- Antecedentes relevantes
- Evolución cronológica
- Diagnósticos principales
- Estudios realizados
- Conducta actual
- Situación funcional

HISTORIAL COMPLETO DEL PACIENTE:
\"\"\"
{data.historial}
\"\"\"
"""

    try:

        print(">>> [GPT] LLAMANDO A OPENAI (RESUMEN)…")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un médico especialista en traumatología. "
                        "Redactas resúmenes clínicos formales."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        resumen = response.choices[0].message.content.strip()

        print(">>> [GPT] RESUMEN GENERADO OK")

        return ClinicalSummaryResponse(resumen=resumen)

    except Exception as e:
        print(">>> [GPT] ERROR RESUMEN")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT Summary: {str(e)}"
        )

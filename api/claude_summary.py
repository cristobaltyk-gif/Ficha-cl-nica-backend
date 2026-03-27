from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic
import traceback

router = APIRouter(prefix="/api/claude", tags=["Claude Resumen Clínico"])


# =========================
# SCHEMAS
# =========================

class ClinicalSummaryRequest(BaseModel):
    historial: str


class ClinicalSummaryResponse(BaseModel):
    resumen: str


# =========================
# PROMPT
# =========================

SYSTEM_PROMPT = (
    "Eres un médico especialista en traumatología. "
    "Redactas resúmenes clínicos formales en tercera persona, "
    "sin markdown, sin encabezados decorativos, en texto continuo."
)

USER_TEMPLATE = """Redacta un resumen clínico integral del paciente basado en su historial completo.

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

HISTORIAL COMPLETO:
\"\"\"
{historial}
\"\"\"
"""


# =========================
# ENDPOINT
# =========================

@router.post("/clinical-summary", response_model=ClinicalSummaryResponse)
def clinical_summary(data: ClinicalSummaryRequest):

    print(">>> [CLAUDE] ENDPOINT /clinical-summary ENTRÓ")

    if not data.historial or not data.historial.strip():
        raise HTTPException(status_code=400, detail="Historial vacío")

    try:
        print(">>> [CLAUDE] LLAMANDO A ANTHROPIC (RESUMEN)…")

        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(historial=data.historial)
                }
            ]
        )

        resumen = message.content[0].text.strip()

        print(">>> [CLAUDE] RESUMEN GENERADO OK")

        return ClinicalSummaryResponse(resumen=resumen)

    except Exception as e:
        print(">>> [CLAUDE] ERROR RESUMEN")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error Claude Summary: {str(e)}")

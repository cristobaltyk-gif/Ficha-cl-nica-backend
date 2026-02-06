from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.openai_client import client
import json

router = APIRouter(prefix="/api/gpt", tags=["GPT Clínico"])

# =========================
# SCHEMAS
# =========================

class ClinicalOrderRequest(BaseModel):
    text: str

class ClinicalOrderResponse(BaseModel):
    atencion: str
    diagnostico: str
    receta: str
    examenes: str
    ordenKinesica: str
    indicaciones: str
    indicacionQuirurgica: str

# =========================
# ENDPOINT
# =========================

@router.post(
    "/clinical-order",
    response_model=ClinicalOrderResponse
)
def clinical_order(data: ClinicalOrderRequest):

    if not data.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")

    prompt = f"""
Eres un médico traumatólogo especialista.

Tu tarea es ordenar el texto clínico dictado durante una consulta médica.

REGLAS ESTRICTAS:
- NO inventes información.
- NO agregues conclusiones no mencionadas.
- Usa español médico formal.
- Corrige gramática y coherencia.
- Si un campo no está presente, déjalo vacío.
- Devuelve SOLO un JSON válido.
- NO uses markdown.
- NO agregues explicaciones.

Devuelve EXACTAMENTE este formato:

{{
  "atencion": "",
  "diagnostico": "",
  "receta": "",
  "examenes": "",
  "ordenKinesica": "",
  "indicaciones": "",
  "indicacionQuirurgica": ""
}}

TEXTO CLÍNICO:
\"\"\"
{data.text}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente médico clínico. Respondes solo JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="GPT devolvió JSON inválido"
            )

        return ClinicalOrderResponse(**parsed)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT: {str(e)}"
        )

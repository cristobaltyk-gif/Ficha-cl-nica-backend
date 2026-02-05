from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.openai_client import client

router = APIRouter(prefix="/api/gpt", tags=["GPT Clínico"])

# =========================
# SCHEMAS
# =========================

class ClinicalOrderRequest(BaseModel):
    text: str

class ClinicalOrderResponse(BaseModel):
    atencion: str
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
Eres un médico traumatólogo experto.
A partir del TEXTO CRUDO de una consulta médica,
ordena la información clínicamente y devuelve SOLO
un JSON con los siguientes campos:

- atencion
- receta
- examenes
- ordenKinesica
- indicaciones
- indicacionQuirurgica

REGLAS:
- No inventes datos
- No agregues explicaciones
- No escribas texto fuera del JSON
- Usa lenguaje médico claro en español
- Si un campo no aplica, déjalo vacío

TEXTO CRUDO:
\"\"\"
{data.text}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente médico clínico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content

        # GPT devuelve JSON → lo parseamos
        result = eval(content)

        return ClinicalOrderResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT: {str(e)}"
        )

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
# HELPERS
# =========================

def _safe_str(value) -> str:
    """
    Asegura string limpio para frontend.
    None, listas o valores raros -> ""
    """
    if isinstance(value, str):
        return value.strip()
    return ""


# =========================
# ENDPOINT
# =========================

@router.post(
    "/clinical-order",
    response_model=ClinicalOrderResponse
)
def clinical_order(data: ClinicalOrderRequest):

    if not data.text or not data.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Texto vacío"
        )

    prompt = f"""
Eres un médico traumatólogo especialista.

Tu tarea es ordenar el texto clínico dictado durante una consulta médica real.

REGLAS ESTRICTAS:
- NO inventes información.
- NO agregues conclusiones no mencionadas.
- Usa español médico formal.
- Corrige gramática y coherencia.
- Si la información clínica está explícitamente mencionada en el texto,
  aunque no esté rotulada como sección,
  ordénala en el campo correspondiente.
- Si un campo NO está mencionado de ninguna forma en el texto,
  déjalo vacío.
- Devuelve SOLO un JSON válido.
- NO uses markdown.
- NO agregues explicaciones.
- NO agregues texto fuera del JSON.

FORMATO DE SALIDA OBLIGATORIO (JSON EXACTO):

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
                    "content": (
                        "Eres un asistente médico clínico. "
                        "Respondes exclusivamente con JSON válido."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        # =========================
        # PARSEO ESTRICTO
        # =========================
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="GPT devolvió JSON inválido. Complete la ficha manualmente."
            )

        # =========================
        # NORMALIZACIÓN (CONTRATO)
        # =========================
        return ClinicalOrderResponse(
            atencion=_safe_str(parsed.get("atencion")),
            diagnostico=_safe_str(parsed.get("diagnostico")),
            receta=_safe_str(parsed.get("receta")),
            examenes=_safe_str(parsed.get("examenes")),
            ordenKinesica=_safe_str(parsed.get("ordenKinesica")),
            indicaciones=_safe_str(parsed.get("indicaciones")),
            indicacionQuirurgica=_safe_str(parsed.get("indicacionQuirurgica")),
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT: {str(e)}"
        )

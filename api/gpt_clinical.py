from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.openai_client import client
import json
import traceback

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
    Normaliza cualquier valor a string seguro para el frontend.
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

    print(">>> [GPT] ENDPOINT /clinical-order ENTRÓ")

    if not data.text or not data.text.strip():
        print(">>> [GPT] TEXTO VACÍO")
        raise HTTPException(
            status_code=400,
            detail="Texto vacío"
        )

    print(">>> [GPT] TEXTO RECIBIDO:")
    print(data.text)

    # =========================
    # PROMPT CLÍNICO RÍGIDO
    # =========================
    prompt = f"""
Eres un médico traumatólogo especialista.

Tu tarea es TRANSFORMAR el texto clínico dictado o escrito durante una consulta
en una ficha clínica formal, objetiva y profesional.

REGLAS ABSOLUTAS:
- NO saludes.
- NO dialogues.
- NO inventes información.
- NO agregues antecedentes no mencionados.
- NO agregues conclusiones propias.
- Usa español médico formal.
- Corrige gramática y coherencia.
- Si una información está claramente mencionada, asígnala al campo correcto,
  aunque no esté rotulada.
- Si un campo NO está mencionado de ninguna forma, déjalo vacío.
- Devuelve SOLO un JSON válido.
- NO markdown.
- NO explicaciones.
- NO texto fuera del JSON.

ESTRUCTURA OBLIGATORIA:

ATENCION:
Debe redactarse como texto clínico formal, usando este esquema SOLO si corresponde:
- Edad del paciente (si está mencionada).
- Antecedentes mórbidos relevantes (si están mencionados).
- Refiere: relato del paciente.
- Examen físico: hallazgos objetivos del médico.

DIAGNOSTICO:
- Debe reflejar el juicio clínico del médico.
- Incluir lateralidad (derecha / izquierda) si corresponde.
- NO repetir síntomas.

EXAMENES:
- Deben ser coherentes con la historia clínica.
- Incluir región anatómica y lateralidad si corresponde.

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
        print(">>> [GPT] LLAMANDO A OPENAI…")

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

        print(">>> [GPT] RESPUESTA OPENAI RECIBIDA")

        content = response.choices[0].message.content
        print(">>> [GPT] CONTENIDO CRUDO:")
        print(content)

        # =========================
        # PARSEO ESTRICTO
        # =========================
        try:
            parsed = json.loads(content)
            print(">>> [GPT] JSON PARSEADO OK")
        except json.JSONDecodeError:
            print(">>> [GPT] ERROR JSON INVÁLIDO")
            raise HTTPException(
                status_code=500,
                detail="GPT devolvió JSON inválido. Complete la ficha manualmente."
            )

        print(">>> [GPT] JSON FINAL ENTREGADO AL FRONT:")
        print(parsed)

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
        print(">>> [GPT] EXCEPCIÓN NO CONTROLADA")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error GPT: {str(e)}"
        )

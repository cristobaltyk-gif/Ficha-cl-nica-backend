from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic
import json
import traceback

router = APIRouter(prefix="/api/claude", tags=["Claude Clínico"])


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


def _safe_str(value) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


SYSTEM_PROMPT = (
    "Eres un médico traumatólogo especialista. "
    "Tu única función es transformar texto clínico en una ficha estructurada. "
    "Respondes exclusivamente con JSON válido, sin markdown, sin explicaciones, sin texto fuera del JSON."
)

USER_TEMPLATE = """Transforma el siguiente texto clínico en una ficha formal.

REGLAS:
- No inventes información no mencionada.
- No agregues antecedentes ausentes.
- Usa español médico formal.
- Si un campo no está mencionado, déjalo vacío ("").
- Incluye lateralidad cuando corresponda.
- Devuelve SOLO el JSON, sin nada más.

CAMPOS REQUERIDOS:
- atencion: texto clínico formal (edad, antecedentes, relato del paciente, examen físico).
- diagnostico: juicio clínico con lateralidad si aplica.
- receta: medicamentos prescritos.
- examenes: imágenes o laboratorio solicitado con región y lateralidad.
- ordenKinesica: órdenes de kinesiología.
- indicaciones: indicaciones post-consulta.
- indicacionQuirurgica: indicación quirúrgica si aplica.

FORMATO DE SALIDA:
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
{text}
\"\"\"
"""


@router.post("/clinical-order", response_model=ClinicalOrderResponse)
def clinical_order(data: ClinicalOrderRequest):

    print(">>> [CLAUDE] ENDPOINT /clinical-order ENTRÓ")

    if not data.text or not data.text.strip():
        print(">>> [CLAUDE] TEXTO VACÍO")
        raise HTTPException(status_code=400, detail="Texto vacío")

    print(">>> [CLAUDE] TEXTO RECIBIDO:")
    print(data.text)

    try:
        print(">>> [CLAUDE] LLAMANDO A ANTHROPIC…")

        client = anthropic.Anthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(text=data.text)
                }
            ]
        )

        print(">>> [CLAUDE] RESPUESTA RECIBIDA")

        content = message.content[0].text
        print(">>> [CLAUDE] CONTENIDO CRUDO:")
        print(content)

        try:
            parsed = json.loads(content)
            print(">>> [CLAUDE] JSON PARSEADO OK")
        except json.JSONDecodeError:
            print(">>> [CLAUDE] ERROR JSON INVÁLIDO")
            raise HTTPException(
                status_code=500,
                detail="Claude devolvió JSON inválido. Complete la ficha manualmente."
            )

        print(">>> [CLAUDE] JSON FINAL ENTREGADO AL FRONT:")
        print(parsed)

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
        print(">>> [CLAUDE] EXCEPCIÓN NO CONTROLADA")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error Claude: {str(e)}")

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic
import json
import traceback

router = APIRouter(prefix="/api/claude", tags=["Claude Kinesiología"])


class KineOrderRequest(BaseModel):
    text: str


class KineOrderResponse(BaseModel):
    atencion: str
    examen_fisico: str
    diagnostico: str
    plan_tratamiento: str


def _safe_str(value) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


SYSTEM_PROMPT = (
    "Eres un kinesiólogo clínico especialista. "
    "Tu única función es transformar texto de sesión kinésica en una ficha estructurada. "
    "Respondes exclusivamente con JSON válido, sin markdown, sin explicaciones, sin texto fuera del JSON."
)

USER_TEMPLATE = """Transforma el siguiente texto de sesión kinésica en una ficha formal.

REGLAS:
- No inventes información no mencionada.
- Usa español clínico formal de kinesiología.
- Si un campo no está mencionado, déjalo vacío ("").
- Incluye lateralidad y región corporal cuando corresponda.
- Devuelve SOLO el JSON, sin nada más.

CAMPOS REQUERIDOS:
- atencion: motivo de consulta, antecedentes relevantes y relato del paciente en formato formal.
- examen_fisico: hallazgos objetivos — rangos articulares, fuerza muscular, postura, pruebas especiales y resultados.
- diagnostico: diagnóstico funcional kinésico con región y lateralidad si aplica.
- plan_tratamiento: objetivos terapéuticos, técnicas a utilizar, frecuencia de sesiones e indicaciones domiciliarias.

FORMATO DE SALIDA:
{{
  "atencion": "",
  "examen_fisico": "",
  "diagnostico": "",
  "plan_tratamiento": ""
}}

TEXTO DE SESIÓN:
\"\"\"
{text}
\"\"\"
"""


@router.post("/kine-order", response_model=KineOrderResponse)
def kine_order(data: KineOrderRequest):

    print(">>> [CLAUDE KINE] ENDPOINT /kine-order ENTRÓ")

    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")

    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(text=data.text)}]
        )

        content = message.content[0].text

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Claude devolvió JSON inválido.")

        return KineOrderResponse(
            atencion=_safe_str(parsed.get("atencion")),
            examen_fisico=_safe_str(parsed.get("examen_fisico")),
            diagnostico=_safe_str(parsed.get("diagnostico")),
            plan_tratamiento=_safe_str(parsed.get("plan_tratamiento")),
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error Claude Kine: {str(e)}")

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from Documentospdf.recetaMedica import generar_receta_pdf
from Documentospdf.informeMedico import generar_informe_pdf
from Documentospdf.ordenKinesiologia import generar_kinesiologia_pdf
from Documentospdf.ordenQuirurgica import generar_quirurgica_pdf


router = APIRouter(
    prefix="/api/pdf",
    tags=["PDF"]
)


# =====================================================
# Helper común
# =====================================================

def build_response(buffer: BytesIO, filename: str):
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}.pdf"
        }
    )


def get_professional_from_header(request: Request) -> str:
    """
    Obtiene el profesional desde el header enviado por frontend.
    El frontend debe enviar:
    X-Internal-User: <usuario_logeado>
    """

    professional = request.headers.get("x-internal-user")

    if not professional:
        raise HTTPException(
            status_code=401,
            detail="Profesional no autorizado"
        )

    return professional


# =====================================================
# RECETA
# =====================================================

@router.post("/receta")
async def receta(request: Request, body: dict):

    professional = get_professional_from_header(request)

    buffer = generar_receta_pdf(body, professional)

    return build_response(buffer, "receta_medica")


# =====================================================
# INFORME MÉDICO
# =====================================================

@router.post("/informe")
async def informe(request: Request, body: dict):

    professional = get_professional_from_header(request)

    buffer = generar_informe_pdf(body, professional)

    return build_response(buffer, "informe_medico")


# =====================================================
# ORDEN KINESIOLÓGICA
# =====================================================

@router.post("/kinesiologia")
async def kinesiologia(request: Request, body: dict):

    professional = get_professional_from_header(request)

    buffer = generar_kinesiologia_pdf(body, professional)

    return build_response(buffer, "orden_kinesiologia")


# =====================================================
# ORDEN QUIRÚRGICA
# =====================================================

@router.post("/quirurgica")
async def quirurgica(request: Request, body: dict):

    professional = get_professional_from_header(request)

    buffer = generar_quirurgica_pdf(body, professional)

    return build_response(buffer, "orden_quirurgica")

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from Documentospdf.recetaMedica import generarRecetaMedica
from Documentospdf.informeMedico import generar_informe_pdf
from Documentospdf.ordenKinesiologia import generarOrdenKinesiologia
from Documentospdf.ordenQuirurgica import generarOrdenQuirurgica

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

    buffer = BytesIO()

    # 🔥 inyectamos el profesional automáticamente
    body["professional"] = professional

    generarRecetaMedica(buffer, body)

    return build_response(buffer, "receta_medica")


# =====================================================
# INFORME MÉDICO
# =====================================================

@router.post("/informe")
async def informe(request: Request, body: dict):

    professional = get_professional_from_header(request)

    # Esta función ya recibe (data, professional_id)
    buffer = generar_informe_pdf(body, professional)

    return build_response(buffer, "informe_medico")


# =====================================================
# ORDEN KINESIOLÓGICA
# =====================================================

@router.post("/kinesiologia")
async def kinesiologia(request: Request, body: dict):

    professional = get_professional_from_header(request)

    body["professional"] = professional

    buffer = generarOrdenKinesiologia(body)

    return build_response(buffer, "orden_kinesiologia")


# =====================================================
# ORDEN QUIRÚRGICA
# =====================================================

@router.post("/quirurgica")
async def quirurgica(request: Request, body: dict):

    professional = get_professional_from_header(request)

    body["professional"] = professional

    buffer = generarOrdenQuirurgica(body)

    return build_response(buffer, "orden_quirurgica")

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO

from auth.internal_auth import require_internal_auth

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

# =====================================================
# RECETA
# =====================================================

@router.post("/receta")
async def receta(
    body: dict,
    auth = Depends(require_internal_auth)
):

    professional = auth["professional"]

    buffer = BytesIO()

    body["professional"] = professional

    generarRecetaMedica(buffer, body)

    return build_response(buffer, "receta_medica")


# =====================================================
# INFORME MÉDICO
# =====================================================

@router.post("/informe")
async def informe(
    body: dict,
    auth = Depends(require_internal_auth)
):

    professional = auth["professional"]

    buffer = generar_informe_pdf(body, professional)

    return build_response(buffer, "informe_medico")


# =====================================================
# ORDEN KINESIOLÓGICA
# =====================================================

@router.post("/kinesiologia")
async def kinesiologia(
    body: dict,
    auth = Depends(require_internal_auth)
):

    professional = auth["professional"]

    body["professional"] = professional

    buffer = generarOrdenKinesiologia(body)

    return build_response(buffer, "orden_kinesiologia")


# =====================================================
# ORDEN QUIRÚRGICA
# =====================================================

@router.post("/quirurgica")
async def quirurgica(
    body: dict,
    auth = Depends(require_internal_auth)
):

    professional = auth["professional"]

    body["professional"] = professional

    buffer = generarOrdenQuirurgica(body)

    return build_response(buffer, "orden_quirurgica")

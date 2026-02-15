from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from pdf.receta import generar_receta_pdf
from pdf.informe import generar_informe_pdf
from pdf.kinesiologia import generar_kinesiologia_pdf
from pdf.quirurgica import generar_quirurgica_pdf

router = APIRouter(prefix="/api/pdf", tags=["PDF"])


# =========================================
# Helper común
# =========================================

def build_response(buffer: BytesIO, filename: str):
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}.pdf"
        },
    )


# =========================================
# RECETA
# =========================================

@router.post("/receta")
async def receta(request: Request, body: dict):

    professional = request.headers.get("x-internal-user")

    if not professional:
        raise HTTPException(status_code=401, detail="Profesional no autorizado")

    buffer = generar_receta_pdf(body, professional)

    return build_response(buffer, "receta_medica")


# =========================================
# INFORME
# =========================================

@router.post("/informe")
async def informe(request: Request, body: dict):

    professional = request.headers.get("x-internal-user")

    if not professional:
        raise HTTPException(status_code=401, detail="Profesional no autorizado")

    buffer = generar_informe_pdf(body, professional)

    return build_response(buffer, "informe_medico")


# =========================================
# KINESIOLOGÍA
# =========================================

@router.post("/kinesiologia")
async def kinesiologia(request: Request, body: dict):

    professional = request.headers.get("x-internal-user")

    if not professional:
        raise HTTPException(status_code=401, detail="Profesional no autorizado")

    buffer = generar_kinesiologia_pdf(body, professional)

    return build_response(buffer, "orden_kinesiologia")


# =========================================
# QUIRÚRGICA
# =========================================

@router.post("/quirurgica")
async def quirurgica(request: Request, body: dict):

    professional = request.headers.get("x-internal-user")

    if not professional:
        raise HTTPException(status_code=401, detail="Profesional no autorizado")

    buffer = generar_quirurgica_pdf(body, professional)

    return build_response(buffer, "orden_quirurgica")

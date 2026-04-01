from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO

from auth.internal_auth import require_internal_auth

from Documentospdf.recetaMedica import generarRecetaMedica
from Documentospdf.informeMedico import generar_informe_pdf
from Documentospdf.ordenKinesiologia import generarOrdenKinesiologia
from Documentospdf.ordenQuirurgica import generarOrdenQuirurgica
from Documentospdf.Examenes import generarOrdenExamenes
from notifications.email_service import enviar_documentos_atencion


router = APIRouter(
    prefix="/api/pdf",
    tags=["PDF"]
)


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
async def receta(body: dict, auth=Depends(require_internal_auth)):
    professional = auth["professional"]
    buffer = BytesIO()
    body["professional"] = professional
    generarRecetaMedica(buffer, body)
    return build_response(buffer, "receta_medica")


# =====================================================
# INFORME MÉDICO
# =====================================================

@router.post("/informe")
async def informe(body: dict, auth=Depends(require_internal_auth)):
    professional = auth["professional"]
    buffer = BytesIO()
    body["professional"] = professional
    generar_informe_pdf(buffer, body)
    return build_response(buffer, "informe_medico")


# =====================================================
# ORDEN KINESIOLÓGICA
# =====================================================

@router.post("/kinesiologia")
async def kinesiologia(body: dict, auth=Depends(require_internal_auth)):
    professional = auth["professional"]
    buffer = BytesIO()
    body["professional"] = professional
    generarOrdenKinesiologia(buffer, body)
    return build_response(buffer, "orden_kinesiologia")


# =====================================================
# ORDEN QUIRÚRGICA
# =====================================================

@router.post("/quirurgica")
async def quirurgica(body: dict, auth=Depends(require_internal_auth)):
    professional = auth["professional"]
    buffer = BytesIO()
    body["professional"] = professional
    generarOrdenQuirurgica(buffer, body)
    return build_response(buffer, "orden_quirurgica")


# =====================================================
# ORDEN DE EXÁMENES
# =====================================================

@router.post("/examenes")
async def examenes(body: dict, auth=Depends(require_internal_auth)):
    professional = auth["professional"]
    buffer = BytesIO()
    body["professional"] = professional
    generarOrdenExamenes(buffer, body)
    return build_response(buffer, "orden_examenes")


# =====================================================
# ENVIAR EMAIL CON TODOS LOS PDFs
# =====================================================

@router.post("/enviar-email")
async def enviar_email_documentos(
    body: dict,
    auth=Depends(require_internal_auth)
):
    """
    Genera todos los documentos que vengan en el body y los envía
    al email del paciente como adjuntos en un solo correo.

    Body esperado:
    {
        email: str,
        nombre_paciente: str,
        fecha: str,
        profesional_nombre: str,
        receta: { ...payload } | null,
        informe: { ...payload } | null,
        kinesiologia: { ...payload } | null,
        examenes: { ...payload } | null,
        quirurgica: { ...payload } | null
    }
    """
    email = body.get("email", "").strip()
    if not email:
        return {"ok": False, "error": "Sin email"}

    professional = auth["professional"]
    nombre_paciente  = body.get("nombre_paciente", "Paciente")
    fecha            = body.get("fecha", "")
    profesional_nombre = body.get("profesional_nombre", professional)

    adjuntos = []

    # Receta
    if body.get("receta"):
        buf = BytesIO()
        payload = body["receta"]
        payload["professional"] = professional
        generarRecetaMedica(buf, payload)
        adjuntos.append(("receta_medica.pdf", buf.getvalue()))

    # Informe
    if body.get("informe"):
        buf = BytesIO()
        payload = body["informe"]
        payload["professional"] = professional
        generar_informe_pdf(buf, payload)
        adjuntos.append(("informe_medico.pdf", buf.getvalue()))

    # Kinesiología
    if body.get("kinesiologia"):
        buf = BytesIO()
        payload = body["kinesiologia"]
        payload["professional"] = professional
        generarOrdenKinesiologia(buf, payload)
        adjuntos.append(("orden_kinesiologia.pdf", buf.getvalue()))

    # Exámenes
    if body.get("examenes"):
        buf = BytesIO()
        payload = body["examenes"]
        payload["professional"] = professional
        generarOrdenExamenes(buf, payload)
        adjuntos.append(("orden_examenes.pdf", buf.getvalue()))

    # Quirúrgica
    if body.get("quirurgica"):
        buf = BytesIO()
        payload = body["quirurgica"]
        payload["professional"] = professional
        generarOrdenQuirurgica(buf, payload)
        adjuntos.append(("orden_quirurgica.pdf", buf.getvalue()))

    if not adjuntos:
        return {"ok": False, "error": "Sin documentos para enviar"}

    ok = enviar_documentos_atencion(
        email_paciente=email,
        nombre_paciente=nombre_paciente,
        fecha=fecha,
        profesional_nombre=profesional_nombre,
        adjuntos=adjuntos
    )

    return {"ok": ok}

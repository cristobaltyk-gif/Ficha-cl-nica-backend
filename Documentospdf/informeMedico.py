# pdf/informe.py

import os
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors

from pdf.professional_resolver import get_professional_data


def generar_informe_pdf(data: dict, professional_id: str):

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=80,
        bottomMargin=80
    )

    elements = []
    styles = getSampleStyleSheet()

    # Estilo clínico más sobrio
    estilo_titulo = styles["Heading1"]
    estilo_seccion = styles["Heading2"]
    estilo_normal = styles["Normal"]

    medico = get_professional_data(professional_id)

    if not medico:
        raise Exception("Profesional no encontrado")

    # ================= LOGO =================
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    logo_path = os.path.join(assets_dir, "ica.jpg")

    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=50))
        elements.append(Spacer(1, 12))

    # ================= ENCABEZADO =================
    elements.append(Paragraph(
        "<b>INSTITUTO DE CIRUGÍA ARTICULAR</b>",
        estilo_titulo
    ))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        "<u>INFORME MÉDICO</u>",
        styles["Heading2"]
    ))
    elements.append(Spacer(1, 20))

    # ================= DATOS PACIENTE =================
    elements.append(Paragraph(f"<b>Nombre:</b> {data.get('nombre','')}", estilo_normal))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"<b>Edad:</b> {data.get('edad','')}", estilo_normal))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"<b>RUT:</b> {data.get('rut','')}", estilo_normal))
    elements.append(Spacer(1, 18))

    # ================= SECCIONES CLÍNICAS =================
    def seccion(titulo, contenido):
        if contenido and str(contenido).strip():
            elements.append(Paragraph(f"<b>{titulo}</b>", estilo_seccion))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(str(contenido).strip(), estilo_normal))
            elements.append(Spacer(1, 14))

    seccion("Motivo de Consulta", data.get("motivoConsulta"))
    seccion("Antecedentes Relevantes", data.get("antecedentes"))
    seccion("Examen Físico", data.get("examenFisico"))
    seccion("Estudios Complementarios", data.get("estudios"))
    seccion("Impresión Diagnóstica", data.get("impresionDiagnostica"))
    seccion("Plan y Conducta", data.get("plan"))

    elements.append(Spacer(1, 40))

    # ================= FIRMA =================
    elements.append(Paragraph("______________________________", estilo_normal))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Firma y Timbre Médico", estilo_normal))
    elements.append(Spacer(1, 12))

    # Firma imagen
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        elements.append(Image(firma_path, width=200, height=60))
        elements.append(Spacer(1, 12))

    # Timbre imagen
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        elements.append(Image(timbre_path, width=100, height=100))
        elements.append(Spacer(1, 12))

    # ================= PIE PROFESIONAL =================
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>{medico.get('nombre','')}</b>", estilo_normal))
    elements.append(Paragraph(f"RUT: {medico.get('rut','')}", estilo_normal))
    elements.append(Paragraph(medico.get("especialidad",""), estilo_normal))
    elements.append(Paragraph("INSTITUTO DE CIRUGÍA ARTICULAR", estilo_normal))

    # ================= BUILD =================
    doc.build(elements)

    buffer.seek(0)
    return buffer

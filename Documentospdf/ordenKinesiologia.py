# Documentospdf/ordenKinesiologia.py

import os
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from Documentospdf.professionalResolver import getProfessionalData


def generarOrdenKinesiologia(datos: dict):

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

    nombre = datos.get("nombre")
    edad = datos.get("edad")
    rut = datos.get("rut")
    diagnostico = datos.get("diagnostico")
    lado = datos.get("lado")
    indicaciones = datos.get("indicaciones")
    professional = datos.get("professional")

    medico = getProfessionalData(professional)

    if not medico:
        raise Exception("Profesional no encontrado")

    assets_dir = os.path.join(os.path.dirname(__file__), "assets")

    # ================= ENCABEZADO =================
    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=50))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        "<b>INSTITUTO DE CIRUGÍA ARTICULAR</b>",
        styles["Heading1"]
    ))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        "<u>ORDEN DE ATENCIÓN KINÉSICA</u>",
        styles["Heading2"]
    ))
    elements.append(Spacer(1, 24))

    # ================= DATOS PACIENTE =================
    elements.append(Paragraph(f"<b>Nombre:</b> {nombre or ''}", styles["Normal"]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph(f"<b>Edad:</b> {edad or ''}", styles["Normal"]))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"<b>RUT:</b> {rut or ''}", styles["Normal"]))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"<b>Diagnóstico:</b> {(diagnostico or '')} {(lado or '')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 24))

    # ================= ORDEN =================
    elements.append(Paragraph(
        "<b><font size=16>10 SESIONES DE KINESIOTERAPIA</font></b>",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 24))

    if indicaciones:
        elements.append(Paragraph("<b>Indicaciones:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(indicaciones, styles["Normal"]))
        elements.append(Spacer(1, 20))

    elements.append(Spacer(1, 40))

    # ================= FIRMA =================
    elements.append(Paragraph("______________________________", styles["Normal"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Firma y Timbre Médico", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Firma
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        elements.append(Image(firma_path, width=200, height=60))
        elements.append(Spacer(1, 12))

    # Timbre
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        elements.append(Image(timbre_path, width=100, height=100))
        elements.append(Spacer(1, 12))

    # ================= PIE =================
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>{medico.get('nombre','')}</b>", styles["Normal"]))
    elements.append(Paragraph(f"RUT: {medico.get('rut','')}", styles["Normal"]))
    elements.append(Paragraph(medico.get("especialidad",""), styles["Normal"]))
    elements.append(Paragraph("INSTITUTO DE CIRUGÍA ARTICULAR", styles["Normal"]))

    doc.build(elements)

    buffer.seek(0)
    return buffer

# Documentospdf/ordenQuirurgica.py

import os
from io import BytesIO
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from Documentospdf.professionalResolver import getProfessionalData


def generarOrdenQuirurgica(datos: dict):

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
    rut = datos.get("rut")
    edad = datos.get("edad")
    diagnostico = datos.get("diagnostico")
    codigoCirugia = datos.get("codigoCirugia")
    tipoCirugia = datos.get("tipoCirugia")
    modalidad = datos.get("modalidad")
    equipoMedico = datos.get("equipoMedico")
    insumos = datos.get("insumos")
    professional = datos.get("professional")

    medico = getProfessionalData(professional)
    if not medico:
        raise Exception("Profesional no encontrado")

    fechaActual = datetime.now().strftime("%d-%m-%Y")

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
        "<u>ORDEN MÉDICA DE INTERVENCIÓN QUIRÚRGICA</u>",
        styles["Heading2"]
    ))
    elements.append(Spacer(1, 16))

    elements.append(Paragraph(
        "<b>IMPORTANTE:</b> Se tomará contacto a la brevedad para confirmar o reagendar fecha de intervención desde la Unidad de Planificación Quirúrgica.",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"Fecha actual: {fechaActual}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 24))

    # ================= DATOS PACIENTE =================
    elements.append(Paragraph("<b>DATOS DEL PACIENTE</b>", styles["Heading3"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Nombre: {nombre or ''}", styles["Normal"]))
    elements.append(Paragraph(f"RUT: {rut or ''}", styles["Normal"]))
    elements.append(Paragraph(f"Edad: {edad or ''}", styles["Normal"]))
    elements.append(Paragraph(f"Diagnóstico: {diagnostico or ''}", styles["Normal"]))
    elements.append(Paragraph(f"Código Cirugía: {codigoCirugia or ''}", styles["Normal"]))

    elements.append(Spacer(1, 24))

    # ================= DATOS INTERVENCIÓN =================
    elements.append(Paragraph("<b>DATOS DE LA INTERVENCIÓN</b>", styles["Heading3"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Tipo de Cirugía: {tipoCirugia or ''}", styles["Normal"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Modalidad: {modalidad or ''}", styles["Normal"]))

    elements.append(Spacer(1, 18))

    # ================= EQUIPO / INSUMOS =================
    if equipoMedico:
        elements.append(Paragraph("<b>Equipo Médico:</b>", styles["Normal"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(equipoMedico, styles["Normal"]))
        elements.append(Spacer(1, 12))

    if insumos:
        elements.append(Paragraph("<b>Insumos / OTS:</b>", styles["Normal"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(insumos, styles["Normal"]))
        elements.append(Spacer(1, 12))

    elements.append(Spacer(1, 40))

    # ================= FIRMA =================
    elements.append(Paragraph("______________________________", styles["Normal"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Firma Médico Tratante", styles["Normal"]))
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

    doc.build(elements)

    buffer.seek(0)
    return buffer

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
from reportlab.lib.enums import TA_CENTER

from Documentospdf.professionalResolver import getProfessionalData


def generar_informe_pdf(data: dict, professional_id: str):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=90,
        bottomMargin=90
    )

    elements = []
    styles = getSampleStyleSheet()

    # =========================
    # ESTILOS ICA
    # =========================

    estilo_titulo = ParagraphStyle(
        'TituloICA',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=16,
        spaceAfter=6
    )

    estilo_subtitulo = ParagraphStyle(
        'SubTituloICA',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        fontSize=14,
        textColor=colors.black,
        spaceAfter=20
    )

    estilo_seccion = ParagraphStyle(
        'SeccionICA',
        parent=styles['Heading2'],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6
    )

    estilo_normal = styles["Normal"]

    # =========================
    # PROFESIONAL
    # =========================

    medico = getProfessionalData(professional_id)

    if not medico:
        raise Exception("Profesional no encontrado")

    # =========================
    # ASSETS
    # =========================

    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    logo_path = os.path.join(assets_dir, "ica.jpg")
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))

    # =========================
    # LOGO
    # =========================

    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=120))
        elements.append(Spacer(1, 20))

    # =========================
    # ENCABEZADO
    # =========================

    elements.append(Paragraph(
        "<b>INSTITUTO DE CIRUGÍA ARTICULAR</b>",
        estilo_titulo
    ))

    elements.append(Paragraph(
        "<b>INFORME MÉDICO</b>",
        estilo_subtitulo
    ))

    # =========================
    # DATOS PACIENTE
    # =========================

    elements.append(Paragraph(
        f"<b>Nombre:</b> {data.get('nombre','')}",
        estilo_normal
    ))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"<b>Edad:</b> {data.get('edad','')}",
        estilo_normal
    ))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(
        f"<b>RUT:</b> {data.get('rut','')}",
        estilo_normal
    ))
    elements.append(Spacer(1, 20))

    # =========================
    # SECCIONES CLÍNICAS
    # =========================

    def seccion(titulo, contenido):
        if contenido and str(contenido).strip():
            elements.append(Paragraph(f"<b>{titulo}</b>", estilo_seccion))
            elements.append(Paragraph(str(contenido).strip(), estilo_normal))
            elements.append(Spacer(1, 12))

    seccion("Motivo de Consulta", data.get("motivoConsulta"))
    seccion("Antecedentes Relevantes", data.get("antecedentes"))
    seccion("Examen Físico", data.get("examenFisico"))
    seccion("Estudios Complementarios", data.get("estudios"))
    seccion("Impresión Diagnóstica", data.get("impresionDiagnostica"))
    seccion("Plan y Conducta", data.get("plan"))

    elements.append(Spacer(1, 40))

    # =========================
    # FIRMA
    # =========================

    elements.append(Paragraph(
        "_____________________________________",
        ParagraphStyle(
            'FirmaLinea',
            parent=styles['Normal'],
            alignment=TA_CENTER
        )
    ))
    elements.append(Spacer(1, 6))

    # Firma imagen
    if os.path.exists(firma_path):
        elements.append(Image(firma_path, width=220, height=80))
        elements.append(Spacer(1, 10))

    # Timbre imagen
    if os.path.exists(timbre_path):
        elements.append(Image(timbre_path, width=110, height=110))
        elements.append(Spacer(1, 10))

    # =========================
    # PIE PROFESIONAL
    # =========================

    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        f"<b>{medico.get('name','')}</b>",
        ParagraphStyle(
            'NombreMedico',
            parent=styles['Normal'],
            alignment=TA_CENTER
        )
    ))

    elements.append(Paragraph(
        medico.get("specialty",""),
        ParagraphStyle(
            'Especialidad',
            parent=styles['Normal'],
            alignment=TA_CENTER
        )
    ))

    elements.append(Paragraph(
        "INSTITUTO DE CIRUGÍA ARTICULAR",
        ParagraphStyle(
            'Instituto',
            parent=styles['Normal'],
            alignment=TA_CENTER
        )
    ))

    # =========================
    # BUILD
    # =========================

    doc.build(elements)

    buffer.seek(0)
    return buffer

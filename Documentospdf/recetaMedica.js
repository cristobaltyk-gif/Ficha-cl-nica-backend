# Documentospdf/recetaMedica.py

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from professionalResolver import getProfessionalData


def generarRecetaMedica(buffer, datos):

    nombre = datos.get("nombre")
    edad = datos.get("edad")
    rut = datos.get("rut")
    diagnostico = datos.get("diagnostico")
    medicamentos = datos.get("medicamentos")
    indicaciones = datos.get("indicaciones")
    professional = datos.get("professional")

    medico = getProfessionalData(professional)

    if not medico:
        raise Exception("Profesional no encontrado")

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    base_dir = os.path.dirname(__file__)
    assets_dir = os.path.join(base_dir, "assets")

    # ================= ENCABEZADO =================
    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(ImageReader(logo_path), 50, height - 100, width=120, preserveAspectRatio=True)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, height - 60, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica", 16)
    c.drawString(180, height - 90, "RECETA MÉDICA")

    y = height - 150

    # ================= DATOS PACIENTE =================
    c.setFont("Helvetica", 14)
    c.drawString(50, y, f"Nombre: {nombre or ''}")
    y -= 25
    c.drawString(50, y, f"Edad: {edad or ''}")
    y -= 20
    c.drawString(50, y, f"RUT: {rut or ''}")
    y -= 20
    c.drawString(50, y, f"Diagnóstico: {diagnostico or ''}")
    y -= 40

    # ================= MEDICAMENTOS =================
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Tratamiento indicado:")
    y -= 30

    c.setFont("Helvetica", 13)

    if isinstance(medicamentos, list) and len(medicamentos) > 0:
        for i, med in enumerate(medicamentos):
            c.drawString(60, y, f"{i+1}. {med.get('nombre','')}")
            y -= 18
            c.drawString(80, y, f"Dosis: {med.get('dosis','')}")
            y -= 18
            c.drawString(80, y, f"Frecuencia: {med.get('frecuencia','')}")
            y -= 18
            c.drawString(80, y, f"Duración: {med.get('duracion','')}")
            y -= 25
    else:
        c.drawString(60, y, "—")
        y -= 30

    # ================= INDICACIONES =================
    if indicaciones and indicaciones.strip():
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Indicaciones:")
        y -= 20

        c.setFont("Helvetica", 12)
        text_obj = c.beginText(50, y)
        text_obj.textLines(indicaciones.strip())
        c.drawText(text_obj)

    # ================= FIRMA =================
    baseY = 170

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, baseY, "_________________________")
    c.drawCentredString(width / 2, baseY - 18, "Firma y Timbre Médico")

    # Firma
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(ImageReader(firma_path), width/2 - 125, baseY + 10, width=250, preserveAspectRatio=True)

    # Timbre
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.saveState()
        c.translate(width/2 + 125, baseY + 40)
        c.rotate(20)
        c.drawImage(ImageReader(timbre_path), 0, 0, width=110, preserveAspectRatio=True)
        c.restoreState()

    # ================= PIE =================
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, baseY - 50, medico.get("nombre", ""))
    c.drawCentredString(width / 2, baseY - 65, f"RUT: {medico.get('rut','')}")
    c.drawCentredString(width / 2, baseY - 80, medico.get("especialidad", ""))
    c.drawCentredString(width / 2, baseY - 95, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

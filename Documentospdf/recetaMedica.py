# Documentospdf/recetaMedica.py

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from Documentospdf.professionalResolver import getProfessionalData


def calcular_edad(fecha_nacimiento_str):
    try:
        nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
        hoy = date.today()
        return hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
    except:
        return ""


def generarRecetaMedica(buffer, datos):

    nombre = datos.get("nombre", "")
    rut = datos.get("rut", "")
    diagnostico = datos.get("diagnostico", "")
    texto_rp = datos.get("indicaciones", "")  # 🔥 vuelve a usar el texto del box
    professional = datos.get("professional")

    edad = datos.get("edad")
    if not edad and datos.get("fecha_nacimiento"):
        edad = calcular_edad(datos.get("fecha_nacimiento"))

    if not edad:
        edad = ""

    medico = getProfessionalData(professional)
    if not medico:
        raise Exception("Profesional no encontrado")

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    base_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(base_dir)
    assets_dir = os.path.join(project_root, "assets")

    # =========================
    # LOGO + ENCABEZADO
    # =========================

    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            ImageReader(logo_path),
            width/2 - 70,
            height - 120,
            width=140,
            preserveAspectRatio=True,
            mask="auto"
        )

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 60, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 85, "RECETA MÉDICA")

    y = height - 160

    # =========================
    # DATOS PACIENTE
    # =========================

    c.setFont("Helvetica", 13)
    c.drawString(60, y, f"Nombre: {nombre}")
    y -= 22
    c.drawString(60, y, f"Edad: {edad}")
    y -= 22
    c.drawString(60, y, f"RUT: {rut}")
    y -= 22
    c.drawString(60, y, f"Diagnóstico: {diagnostico}")
    y -= 50

    # =========================
    # Rp.
    # =========================

    c.setFont("Helvetica-Bold", 20)
    c.drawString(60, y, "Rp.")
    y -= 35

    c.setFont("Helvetica", 14)

    if texto_rp:
        text_obj = c.beginText(80, y)
        text_obj.setLeading(20)
        text_obj.textLines(texto_rp)
        c.drawText(text_obj)
    else:
        c.drawString(80, y, "_______________________________")

    # =========================
    # FIRMA Y TIMBRE ABAJO
    # =========================

    baseY = 110

    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            ImageReader(firma_path),
            width/2 - 120,
            baseY + 30,
            width=240,
            preserveAspectRatio=True,
            mask="auto"
        )

    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.saveState()
        c.translate(width/2 + 90, baseY + 70)
        c.rotate(15)
        c.drawImage(
            ImageReader(timbre_path),
            0,
            0,
            width=110,
            preserveAspectRatio=True,
            mask="auto"
        )
        c.restoreState()

    # Línea firma
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, baseY, "_____________________________________")
    c.drawCentredString(width/2, baseY - 15, medico.get("name", ""))
    c.drawCentredString(width/2, baseY - 30, medico.get("specialty", ""))
    c.drawCentredString(width/2, baseY - 45, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

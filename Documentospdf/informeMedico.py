# Documentospdf// informemedixo.py

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


def generar_informe_pdf(buffer, datos):

    # =========================
    # PACIENTE
    # =========================

    nombre = datos.get("nombre", "")
    apellido_paterno = datos.get("apellido_paterno", "")
    apellido_materno = datos.get("apellido_materno", "")

    nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}".strip()

    rut = datos.get("rut", "")
    diagnostico = datos.get("diagnostico", "")
    texto_rp = datos.get("indicaciones", "")
    professional = datos.get("professional")

    edad = datos.get("edad")
    if not edad and datos.get("fecha_nacimiento"):
        edad = calcular_edad(datos.get("fecha_nacimiento"))
    if not edad:
        edad = ""

    # =========================
    # PROFESIONAL
    # =========================

    medico = getProfessionalData(professional)
    if not medico:
        raise Exception("Profesional no encontrado")

    # =========================
    # CANVAS
    # =========================

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    # =========================
    # LOGO (alineación fina, mismo tamaño)
    # =========================

    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            ImageReader(logo_path),
            60,
            height - 155,  # pequeño ajuste vertical
            width=110,
            height=110,
            preserveAspectRatio=True,
            mask="auto"
        )

    # =========================
    # ENCABEZADO (mejor centrado visual)
    # =========================

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 55, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 78, "INFORME MEDICO")

    y = height - 170

    # =========================
    # DATOS PACIENTE (espaciado más armónico)
    # =========================

    c.setFont("Helvetica", 12)

    c.drawString(60, y, f"Nombre: {nombre_completo}")
    y -= 28

    c.drawString(60, y, f"Edad: {edad}")
    y -= 28

    c.drawString(60, y, f"RUT: {rut}")
    y -= 28

    c.drawString(60, y, f"Diagnóstico: {diagnostico}")
    y -= 45

    # =========================
    # Rp.
    # =========================

    c.setFont("Helvetica-Bold", 18)
    c.drawString(60, y, "Rp.")
    y -= 55

    c.setFont("Helvetica", 13)

    if texto_rp:
        text_obj = c.beginText(75, y)
        text_obj.setLeading(18)
        text_obj.textLines(texto_rp)
        c.drawText(text_obj)
    else:
        c.drawString(75, y, "____________________________")

    # =========================
    # FIRMA Y TIMBRE
    # =========================

    baseY = 110

    # FIRMA (misma posición, pequeño ajuste visual)
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            ImageReader(firma_path),
            width/2 - 110,
            baseY + 30,
            width=220,
            height=85,
            preserveAspectRatio=True,
            mask="auto"
        )

    # TIMBRE (rotado, mismo tamaño)
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):

        c.saveState()

        timbre_x = width/2 + 95
        timbre_y = baseY + 35
        timbre_width = 95
        timbre_height = 95

        c.translate(
            timbre_x + timbre_width / 2,
            timbre_y + timbre_height / 2
        )

        c.rotate(-20)

        c.drawImage(
            ImageReader(timbre_path),
            -timbre_width / 2,
            -timbre_height / 2,
            width=timbre_width,
            height=timbre_height,
            preserveAspectRatio=True,
            mask="auto"
        )

        c.restoreState()

    # =========================
    # LÍNEA Y NOMBRE PROFESIONAL
    # =========================

    c.setFont("Helvetica", 11)

    c.drawCentredString(width/2, baseY, "_____________________________________")
    c.drawCentredString(width/2, baseY - 16, medico.get("name", ""))
    c.drawCentredString(width/2, baseY - 30, medico.get("specialty", ""))
    c.drawCentredString(width/2, baseY - 44, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

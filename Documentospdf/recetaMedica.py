# Documentospdf/recetaMedica.py

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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
    texto_rp = datos.get("indicaciones", "")
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

    # ===== RUTAS ABSOLUTAS CORRECTAS =====

    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    # ===== LOGO IZQUIERDA (FIJO) =====

    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            50,                 # izquierda
            height - 95,        # arriba
            width=130,
            height=55           # tamaño fijo, sin preserveAspectRatio
        )

    # ===== ENCABEZADO ALINEADO =====

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 55, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 75, "RECETA MÉDICA")

    y = height - 150

    # ===== DATOS PACIENTE =====

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Nombre: {nombre}")
    y -= 20
    c.drawString(50, y, f"Edad: {edad}")
    y -= 20
    c.drawString(50, y, f"RUT: {rut}")
    y -= 20
    c.drawString(50, y, f"Diagnóstico: {diagnostico}")
    y -= 40

    # ===== Rp =====

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Rp.")
    y -= 30

    c.setFont("Helvetica", 13)

    if texto_rp:
        text_obj = c.beginText(70, y)
        text_obj.setLeading(18)
        text_obj.textLines(texto_rp)
        c.drawText(text_obj)
    else:
        c.drawString(70, y, "____________________________")

    # ===== FIRMA Y TIMBRE ABAJO =====

    baseY = 110

    # Firma
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            firma_path,
            width/2 - 120,
            baseY + 25,
            width=240,
            height=60
        )

    # Timbre superpuesto a la firma
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.drawImage(
            timbre_path,
            width/2 + 70,
            baseY + 35,
            width=90,
            height=90
        )

    # Línea + nombre
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, baseY, "_____________________________________")
    c.drawCentredString(width/2, baseY - 15, medico.get("name", ""))
    c.drawCentredString(width/2, baseY - 30, medico.get("specialty", ""))
    c.drawCentredString(width/2, baseY - 45, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

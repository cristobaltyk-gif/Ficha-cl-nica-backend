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
    texto_rp = datos.get("indicaciones", "")
    professional = datos.get("professional")

    # Edad automática
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

    # ===== RUTAS =====

    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    # ===== LOGO IZQUIERDA =====

    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            50,
            height - 100,
            width=150,
            height=70,
            preserveAspectRatio=True,
            mask='auto'
        )

    # ===== ENCABEZADO =====

    c.setFont("Helvetica-Bold", 15)
    c.drawString(220, height - 55, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 18)
    c.drawString(220, height - 80, "RECETA MÉDICA")

    y = height - 170

    # ===== DATOS PACIENTE (SIN DIAGNÓSTICO) =====

    c.setFont("Helvetica", 12)
    c.drawString(60, y, f"Nombre: {nombre}")
    y -= 22
    c.drawString(60, y, f"Edad: {edad}")
    y -= 22
    c.drawString(60, y, f"RUT: {rut}")
    y -= 40

    # ===== Rp =====

    c.setFont("Helvetica-Bold", 20)
    c.drawString(60, y, "Rp.")
    y -= 35

    c.setFont("Helvetica", 13)

    if texto_rp:
        text_obj = c.beginText(80, y)
        text_obj.setLeading(20)
        text_obj.textLines(texto_rp)
        c.drawText(text_obj)
    else:
        c.drawString(80, y, "______________________________")

    # ===== FIRMA Y TIMBRE ABAJO (PROPORCIONALES) =====

    baseY = 115

    # Firma proporcional (no aplastada)
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            firma_path,
            width/2 - 140,
            baseY + 35,
            width=280,
            preserveAspectRatio=True,
            mask='auto'
        )

    # Timbre proporcional
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.drawImage(
            timbre_path,
            width/2 + 100,
            baseY + 45,
            width=110,
            preserveAspectRatio=True,
            mask='auto'
        )

    # Línea y datos profesional
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, baseY, "________________________________________")
    c.drawCentredString(width/2, baseY - 15, medico.get("nombre", ""))
    c.drawCentredString(width/2, baseY - 30, medico.get("especialidad", ""))
    c.drawCentredString(width/2, baseY - 45, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

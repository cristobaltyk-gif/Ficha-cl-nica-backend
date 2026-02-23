# Documentospdf/recetaMedica.py

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from Documentospdf.professionalResolver import getProfessionalData


# =========================================================
# CALCULAR EDAD AUTOMÁTICA
# =========================================================

def calcular_edad(fecha_nacimiento_str):
    try:
        nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
        hoy = date.today()
        return hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
    except:
        return ""


# =========================================================
# RECETA MÉDICA ESTILO REAL
# =========================================================

def generarRecetaMedica(buffer, datos):

    nombre = datos.get("nombre", "")
    rut = datos.get("rut", "")
    diagnostico = datos.get("diagnostico", "")
    medicamentos = datos.get("medicamentos", [])
    professional = datos.get("professional")

    # Edad automática
    edad = datos.get("edad")
    if not edad and datos.get("fecha_nacimiento"):
        edad = calcular_edad(datos.get("fecha_nacimiento"))

    medico = getProfessionalData(professional)
    if not medico:
        raise Exception("Profesional no encontrado")

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # =========================================================
    # RUTAS
    # =========================================================

    base_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(base_dir)
    assets_dir = os.path.join(project_root, "assets")

    # =========================================================
    # LOGO
    # =========================================================

    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            ImageReader(logo_path),
            50,
            height - 110,
            width=130,
            preserveAspectRatio=True,
            mask="auto"
        )

    # =========================================================
    # TITULO
    # =========================================================

    c.setFont("Helvetica-Bold", 18)
    c.drawString(200, height - 60, "RECETA MÉDICA")

    y = height - 160

    # =========================================================
    # DATOS PACIENTE
    # =========================================================

    c.setFont("Helvetica", 13)
    c.drawString(50, y, f"Nombre: {nombre}")
    y -= 22
    c.drawString(50, y, f"Edad: {edad}")
    y -= 22
    c.drawString(50, y, f"RUT: {rut}")
    y -= 22
    c.drawString(50, y, f"Diagnóstico: {diagnostico}")
    y -= 50

    # =========================================================
    # Rp.
    # =========================================================

    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, y, "Rp.")
    y -= 40

    c.setFont("Helvetica", 14)

    if isinstance(medicamentos, list) and len(medicamentos) > 0:
        for med in medicamentos:
            c.drawString(80, y, f"- {med.get('nombre','')}")
            y -= 20
            c.drawString(100, y, f"{med.get('dosis','')} | {med.get('frecuencia','')} | {med.get('duracion','')}")
            y -= 30
    else:
        c.drawString(80, y, "- ____________________________")
        y -= 30

    # =========================================================
    # FIRMA Y TIMBRE (MUCHO MÁS ABAJO)
    # =========================================================

    baseY = 120

    # Línea
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, baseY, "________________________________________")
    c.drawCentredString(width / 2, baseY - 15, "Firma y Timbre Médico")

    # Firma
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            ImageReader(firma_path),
            width/2 - 140,
            baseY + 15,
            width=280,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Timbre
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.saveState()
        c.translate(width/2 + 130, baseY + 40)
        c.rotate(20)
        c.drawImage(
            ImageReader(timbre_path),
            0,
            0,
            width=120,
            preserveAspectRatio=True,
            mask="auto"
        )
        c.restoreState()

    # =========================================================
    # PIE PROFESIONAL
    # =========================================================

    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, baseY - 40, medico.get("name", ""))
    c.drawCentredString(width / 2, baseY - 55, medico.get("specialty", ""))
    c.drawCentredString(width / 2, baseY - 70, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

# Documentospdf/recetaMedica.py

import os
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from Documentospdf.professionalResolver import getProfessionalData


# =========================================================
# CALCULAR EDAD AUTOMÁTICA
# =========================================================
def calcular_edad(fecha_nacimiento_str: str):
    if not fecha_nacimiento_str:
        return ""

    # Soporta "YYYY-MM-DD" y "DD-MM-YYYY"
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            nacimiento = datetime.strptime(fecha_nacimiento_str, fmt).date()
            hoy = date.today()
            return hoy.year - nacimiento.year - (
                (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
            )
        except Exception:
            continue

    return ""


# =========================================================
# RECETA MÉDICA (FORMATO ICA)
# - Logo arriba izquierda
# - Datos paciente (Nombre completo, Edad, RUT)
# - Rp. (texto del box)
# - Firma + timbre ABAJO, sobre el nombre del médico
# =========================================================
def generarRecetaMedica(buffer, datos: dict):

    # -------------------------
    # PACIENTE (nombre completo)
    # -------------------------
    nombre = (datos.get("nombre") or "").strip()

    # soporta snake_case y camelCase
    apellido_p = (datos.get("apellido_paterno") or datos.get("apellidoPaterno") or "").strip()
    apellido_m = (datos.get("apellido_materno") or datos.get("apellidoMaterno") or "").strip()

    nombre_completo = " ".join([x for x in [nombre, apellido_p, apellido_m] if x]).strip()

    rut = (datos.get("rut") or "").strip()

    # -------------------------
    # EDAD (preferir edad, si no calcular por fecha_nacimiento)
    # -------------------------
    edad = datos.get("edad")
    if not edad:
        fn = datos.get("fecha_nacimiento") or datos.get("fechaNacimiento")
        edad = calcular_edad(fn)

    if edad is None:
        edad = ""

    # -------------------------
    # TEXTO Rp (viene del box)
    # -------------------------
    texto_rp = (datos.get("indicaciones") or "").strip()

    # -------------------------
    # PROFESIONAL
    # -------------------------
    professional = datos.get("professional")
    medico = getProfessionalData(professional)
    if not medico:
        raise Exception("Profesional no encontrado")

    medico_nombre = medico.get("name") or medico.get("nombre") or ""
    medico_especialidad = medico.get("specialty") or medico.get("especialidad") or ""

    # -------------------------
    # PDF
    # -------------------------
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # RUTAS
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    # =========================================================
    # LOGO (ARRIBA IZQUIERDA)
    # =========================================================
    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            logo_path,
            50,
            height - 95,
            width=130,
            preserveAspectRatio=True,
            mask="auto"
        )

    # =========================================================
    # ENCABEZADO (CUADRADO, NO APLASTADO)
    # =========================================================
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 55, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 75, "RECETA MÉDICA")

    # =========================================================
    # DATOS PACIENTE (CON APELLIDOS + EDAD)
    # =========================================================
    y = height - 150

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Nombre: {nombre_completo}")
    y -= 20
    c.drawString(50, y, f"Edad: {edad}")
    y -= 20
    c.drawString(50, y, f"RUT: {rut}")
    y -= 40

    # =========================================================
    # Rp.
    # =========================================================
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

    # =========================================================
    # FIRMA + TIMBRE ABAJO (SOBRE NOMBRE MÉDICO)
    # =========================================================
    baseY = 110

    # Firma
    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            firma_path,
            width / 2 - 120,
            baseY + 25,
            width=240,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Timbre (superpuesto a firma)
    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.drawImage(
            timbre_path,
            width / 2 + 70,
            baseY + 35,
            width=90,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Línea + datos profesional (ABAJO DE FIRMA/TIMBRE)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, baseY, "_____________________________________")
    c.drawCentredString(width / 2, baseY - 15, medico_nombre)
    c.drawCentredString(width / 2, baseY - 30, medico_especialidad)
    c.drawCentredString(width / 2, baseY - 45, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

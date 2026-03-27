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


def wrap_text(text, font_name, font_size, max_width, canvas_obj):
    """Divide texto en líneas que no excedan max_width."""
    canvas_obj.setFont(font_name, font_size)
    words  = text.split()
    lines  = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        if canvas_obj.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_wrapped_text(c, text, x, y, font_name, font_size, max_width, leading, min_y):
    """
    Dibuja texto con wrap. Crea nueva página si se acaba el espacio.
    Devuelve la posición Y final.
    """
    paragraphs = text.split("\n")
    c.setFont(font_name, font_size)

    for para in paragraphs:
        if not para.strip():
            y -= leading * 0.5
            continue

        lines = wrap_text(para, font_name, font_size, max_width, c)

        for line in lines:
            if y < min_y:
                c.showPage()
                y = A4[1] - 60
                c.setFont(font_name, font_size)

            c.drawString(x, y, line)
            y -= leading

        y -= leading * 0.3  # espacio entre párrafos

    return y


def generar_informe_pdf(buffer, datos):

    # =========================
    # PACIENTE
    # =========================
    nombre           = datos.get("nombre", "")
    apellido_paterno = datos.get("apellido_paterno", "")
    apellido_materno = datos.get("apellido_materno", "")
    nombre_completo  = f"{nombre} {apellido_paterno} {apellido_materno}".strip()

    rut        = datos.get("rut", "")
    diagnostico = datos.get("diagnostico", "")
    texto_rp   = datos.get("indicaciones", "")
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
    assets_dir  = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    MARGIN_LEFT  = 60
    MARGIN_RIGHT = 60
    TEXT_WIDTH   = width - MARGIN_LEFT - MARGIN_RIGHT  # ~475pt
    MIN_Y        = 160  # espacio para firma

    # =========================
    # LOGO
    # =========================
    logo_path = os.path.join(assets_dir, "ica.jpg")
    if os.path.exists(logo_path):
        c.drawImage(
            ImageReader(logo_path),
            MARGIN_LEFT, height - 155,
            width=110, height=110,
            preserveAspectRatio=True, mask="auto"
        )

    # =========================
    # ENCABEZADO
    # =========================
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, height - 55, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 78, "INFORME MEDICO")

    y = height - 170

    # =========================
    # DATOS PACIENTE
    # =========================
    c.setFont("Helvetica", 12)
    c.drawString(MARGIN_LEFT, y, f"Nombre: {nombre_completo}")
    y -= 24

    c.drawString(MARGIN_LEFT, y, f"Edad: {edad}")
    y -= 24

    c.drawString(MARGIN_LEFT, y, f"RUT: {rut}")
    y -= 24

    # Diagnóstico con wrap
    diag_lines = wrap_text(f"Diagnóstico: {diagnostico}", "Helvetica", 12, TEXT_WIDTH, c)
    for line in diag_lines:
        c.drawString(MARGIN_LEFT, y, line)
        y -= 20
    y -= 20

    # =========================
    # Rp.
    # =========================
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN_LEFT, y, "Rp.")
    y -= 40

    # =========================
    # TEXTO CLÍNICO CON WRAP
    # =========================
    if texto_rp:
        y = draw_wrapped_text(
            c, texto_rp,
            x=MARGIN_LEFT + 15,
            y=y,
            font_name="Helvetica",
            font_size=12,
            max_width=TEXT_WIDTH - 15,
            leading=18,
            min_y=MIN_Y
        )
    else:
        c.setFont("Helvetica", 12)
        c.drawString(MARGIN_LEFT + 15, y, "____________________________")

    # =========================
    # FIRMA Y TIMBRE
    # =========================
    baseY = 110

    firma_path = os.path.join(assets_dir, medico.get("firma", ""))
    if os.path.exists(firma_path):
        c.drawImage(
            ImageReader(firma_path),
            width / 2 - 110, baseY + 30,
            width=220, height=85,
            preserveAspectRatio=True, mask="auto"
        )

    timbre_path = os.path.join(assets_dir, medico.get("timbre", ""))
    if os.path.exists(timbre_path):
        c.saveState()
        timbre_x = width / 2 + 95
        timbre_y = baseY + 35
        tw = th = 95
        c.translate(timbre_x + tw / 2, timbre_y + th / 2)
        c.rotate(-20)
        c.drawImage(
            ImageReader(timbre_path),
            -tw / 2, -th / 2,
            width=tw, height=th,
            preserveAspectRatio=True, mask="auto"
        )
        c.restoreState()

    # =========================
    # LÍNEA Y NOMBRE PROFESIONAL
    # =========================
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, baseY,      "_____________________________________")
    c.drawCentredString(width / 2, baseY - 16, medico.get("name", ""))
    c.drawCentredString(width / 2, baseY - 30, medico.get("specialty", ""))
    c.drawCentredString(width / 2, baseY - 44, "INSTITUTO DE CIRUGÍA ARTICULAR")

    c.showPage()
    c.save()

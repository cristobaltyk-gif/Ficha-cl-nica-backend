"""
modules/profesionales/timbre_generator.py
Genera timbre profesional con Pillow.
"""
from __future__ import annotations
import io
import math
from PIL import Image, ImageDraw, ImageFont
from db.supabase_client import _get_conn, get_users, get_suscripcion

TITULO_POR_ROL = {
    "medico":    "Dr.",
    "kine":      "Klgo.",
    "psicologo": "Psic.",
}

ICA_CENTRO = "INSTITUTO DE CIRUGÍA ARTICULAR"


def _get_centro_nombre(professional_id: str) -> str:
    """Obtiene el nombre del centro según el scope del profesional."""
    users = get_users()
    user  = users.get(professional_id, {})
    scope = (user.get("role") or {}).get("scope", "ica")

    if scope == "ica":
        return ICA_CENTRO

    # Buscar en suscripciones
    s = get_suscripcion(scope)
    if s:
        return s.get("nombre_centro", scope).upper()
    return scope.upper()


def _get_especialidad_timbre(professional_id: str, specialty: str, rol: str) -> str:
    """Construye el texto inferior del timbre."""
    return specialty or rol.capitalize()


def _draw_text_on_arc(draw, text, cx, cy, radius, start_angle, font, fill, clockwise=True):
    """Dibuja texto curvo sobre un arco."""
    text_len = len(text)
    # Calcular ángulo total que ocupa el texto
    char_angle = 360 / max(text_len * 3.5, 1)
    total_angle = char_angle * text_len

    if clockwise:
        angles = [start_angle + i * char_angle for i in range(text_len)]
    else:
        angles = [start_angle - i * char_angle for i in range(text_len)]

    for i, char in enumerate(text):
        angle_rad = math.radians(angles[i])
        x = cx + radius * math.cos(angle_rad)
        y = cy + radius * math.sin(angle_rad)

        # Rotar cada carácter
        char_img = Image.new("RGBA", (40, 40), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((20, 20), char, font=font, fill=fill, anchor="mm")

        rot_angle = angles[i] + 90 if clockwise else angles[i] - 90
        char_img = char_img.rotate(-rot_angle, expand=False)

        draw._image.paste(char_img, (int(x) - 20, int(y) - 20), char_img)


def generar_timbre(professional_id: str) -> bytes:
    """
    Genera timbre circular para un profesional.
    Retorna bytes PNG con fondo transparente.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM profesionales WHERE id = %s", (professional_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Profesional {professional_id} no encontrado")
            prof = dict(row)

    users = get_users()
    user  = users.get(professional_id, {})
    rol   = (user.get("role") or {}).get("name", "medico")

    nombre    = prof.get("name", "").upper()
    rut       = prof.get("rut", "")
    specialty = prof.get("specialty", "")
    titulo    = TITULO_POR_ROL.get(rol, "")
    centro    = _get_centro_nombre(professional_id)
    especialidad_texto = _get_especialidad_timbre(professional_id, specialty, rol)

    # ── Canvas ──────────────────────────────────────────────
    size   = 500
    cx, cy = size // 2, size // 2
    img    = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw   = ImageDraw.Draw(img)

    color = (0, 0, 0, 255)

    # ── Círculos ─────────────────────────────────────────────
    r_outer = 230
    r_inner = 210
    r_text  = 175

    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
                 outline=color, width=4)
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
                 outline=color, width=2)

    # ── Fuentes ───────────────────────────────────────────────
    try:
        font_arc_lg  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 22)
        font_arc_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 18)
        font_titulo  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 28)
        font_nombre  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 32)
        font_rut     = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 26)
        font_label   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 20)
    except:
        font_arc_lg  = ImageFont.load_default()
        font_arc_sm  = ImageFont.load_default()
        font_titulo  = ImageFont.load_default()
        font_nombre  = ImageFont.load_default()
        font_rut     = ImageFont.load_default()
        font_label   = ImageFont.load_default()

    # ── Texto arco superior (centro) ─────────────────────────
    _draw_text_on_arc(draw, centro, cx, cy,
                      radius=r_text + 15,
                      start_angle=-150,
                      font=font_arc_lg,
                      fill=color,
                      clockwise=True)

    # ── Texto arco inferior (especialidad) ───────────────────
    _draw_text_on_arc(draw, especialidad_texto, cx, cy,
                      radius=r_text + 15,
                      start_angle=30,
                      font=font_arc_sm,
                      fill=color,
                      clockwise=False)

    # ── Texto interior ────────────────────────────────────────
    y_start = cy - 80

    # Título
    draw.text((cx, y_start), titulo, font=font_titulo, fill=color, anchor="mm")
    y_start += 40

    # Nombre (puede ser largo, dividir en dos líneas)
    partes = nombre.split(" ")
    if len(partes) >= 2:
        linea1 = partes[0]
        linea2 = " ".join(partes[1:])
        draw.text((cx, y_start), linea1, font=font_nombre, fill=color, anchor="mm")
        y_start += 38
        draw.text((cx, y_start), linea2, font=font_nombre, fill=color, anchor="mm")
    else:
        draw.text((cx, y_start), nombre, font=font_nombre, fill=color, anchor="mm")
    y_start += 42

    # RUT
    draw.text((cx, y_start), rut, font=font_rut, fill=color, anchor="mm")
    y_start += 30

    # Línea separadora
    draw.line([cx - 60, y_start, cx + 60, y_start], fill=color, width=2)
    y_start += 18

    # Label RUT
    draw.text((cx, y_start), "RUT", font=font_label, fill=color, anchor="mm")

    # ── Exportar ──────────────────────────────────────────────
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

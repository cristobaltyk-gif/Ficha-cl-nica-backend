"""
notifications/email_service.py
"""

import os
import base64
import resend
from typing import List, Tuple

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL     = "Instituto de Cirugía Articular <contacto@icarticular.cl>"
BACKEND_URL    = os.getenv("BACKEND_URL", "https://services.icarticular.cl")
PREDIAG_URL    = "https://app.icarticular.cl"

LOGO_URL = "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300"


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


def _bloque_prediagnostico(
    nombre: str,
    rut: str = "",
    edad: int | None = None,
    sexo: str = "",
) -> str:
    from urllib.parse import urlencode
    params: dict = {
        "nombre": nombre,
        "rut":    rut,
        "origen": "reserva",
    }
    if edad:   params["edad"]   = str(edad)
    if sexo:   params["genero"] = sexo
    link = f"{PREDIAG_URL}?{urlencode(params)}"
    return f"""
    <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
                padding: 18px 20px; margin: 24px 0;">
        <p style="margin: 0 0 8px 0; font-weight: bold; color: #1e3a5f; font-size: 15px;">
            🩺 ¿Quiere llegar preparado a su consulta?
        </p>
        <p style="margin: 0 0 12px 0; color: #334155; font-size: 13px; line-height: 1.5;">
            Nuestro asistente de <strong>prediagnóstico con IA</strong> puede sugerirle
            los exámenes que necesitará antes de su cita, validados por su médico.
            Ahorre tiempo y llegue listo.
        </p>
        <a href="{link}" style="
            display: inline-block;
            background: #1d4ed8;
            color: white;
            padding: 11px 22px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 13px;
        ">Iniciar prediagnóstico IA →</a>
        <p style="margin: 10px 0 0 0; font-size: 11px; color: #94a3b8;">
            Servicio opcional con valor. No reemplaza la consulta médica.
        </p>
    </div>
    """


# ======================================================
# 1. CONFIRMACIÓN DE RESERVA
# ======================================================

def enviar_confirmacion_reserva(
    *,
    email_paciente: str,
    nombre_paciente: str,
    rut_paciente: str = "",
    fecha: str,
    hora: str,
    profesional_nombre: str,
    edad_paciente: int | None = None,
    sexo_paciente: str = "",
) -> bool:
    _init()

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="Instituto de Cirugía Articular" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Reserva confirmada</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su hora ha sido reservada exitosamente en el Instituto de Cirugía Articular:</p>
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
        </div>
        <p>Por favor llegue 10 minutos antes de su hora. Si necesita cancelar o reagendar,
        contáctenos a <a href="mailto:contacto@icarticular.cl">contacto@icarticular.cl</a>.</p>

        {_bloque_prediagnostico(nombre_paciente, rut_paciente, edad_paciente, sexo_paciente)}

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile<br/>
            contacto@icarticular.cl
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": f"ICA — Reserva confirmada · {fecha} {hora}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL reserva: {e}")
        return False


# ======================================================
# 2. CONFIRMACIÓN DE CONTROL GRATUITO
# ======================================================

def enviar_confirmacion_gratuito(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    token: str
) -> bool:
    _init()

    link = f"{BACKEND_URL}/api/control/confirmar?token={token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="Instituto de Cirugía Articular" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Confirmación de atención sin costo</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su próxima atención ha sido marcada como <strong>control gratuito</strong>.
        Por favor confirme haciendo click en el botón:</p>
        <a href="{link}" style="
            display: inline-block;
            background: #0f172a;
            color: white;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 15px;
            margin: 20px 0;
        ">✓ Confirmar atención gratuita</a>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0; color: #16a34a; font-weight: bold;">Esta atención no tiene costo para usted.</p>
        </div>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Si no solicitó esta atención, ignore este mensaje.<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": "Su próxima atención en ICA es sin costo",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL gratuito: {e}")
        return False


# ======================================================
# 3. CONFIRMACIÓN SOBRE CUPO
# ======================================================

def enviar_confirmacion_sobrecupo(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    token: str,
    gratuito: bool = False,
) -> bool:
    _init()

    link = f"{BACKEND_URL}/api/sobrecupo/confirmar?token={token}"

    if gratuito:
        badge_color  = "#16a34a"
        badge_bg     = "#f0fdf4"
        badge_border = "#86efac"
        badge_texto  = "Esta atención no tiene costo para usted."
        asunto       = f"ICA — Sobre cupo sin costo · {fecha} {hora}"
        titulo       = "Confirmación de sobre cupo gratuito"
        btn_texto    = "✓ Confirmar sobre cupo gratuito"
    else:
        badge_color  = "#1d4ed8"
        badge_bg     = "#eff6ff"
        badge_border = "#bfdbfe"
        badge_texto  = "Esta atención tiene el valor normal de consulta."
        asunto       = f"ICA — Sobre cupo agendado · {fecha} {hora}"
        titulo       = "Confirmación de sobre cupo"
        btn_texto    = "✓ Confirmar sobre cupo"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="Instituto de Cirugía Articular" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">{titulo}</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Se ha agendado un <strong>sobre cupo</strong> para usted fuera del horario habitual.
        Por favor confirme su asistencia haciendo click en el botón:</p>
        <a href="{link}" style="
            display: inline-block;
            background: #0f172a;
            color: white;
            padding: 14px 28px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 15px;
            margin: 20px 0;
        ">{btn_texto}</a>
        <div style="background: {badge_bg}; border: 1px solid {badge_border}; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0; color: {badge_color}; font-weight: bold;">{badge_texto}</p>
            <p style="margin: 8px 0 0; font-size: 12px; color: #64748b;">
                ⏳ Esta hora está pendiente de aprobación final por el médico.
            </p>
        </div>
        <p>Por favor llegue 10 minutos antes de su hora.</p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Si no solicitó esta atención, ignore este mensaje.<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": asunto,
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL sobrecupo: {e}")
        return False


# ======================================================
# 4. DOCUMENTOS DE ATENCIÓN
# ======================================================

def enviar_documentos_atencion(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    profesional_nombre: str,
    adjuntos: List[Tuple[str, bytes]]
) -> bool:
    _init()

    nombres = [a[0].replace(".pdf", "").replace("_", " ").title() for a in adjuntos]
    lista_docs = "".join(f"<li>{n}</li>" for n in nombres)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="Instituto de Cirugía Articular" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Documentos de su atención médica</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Adjunto encontrará los documentos generados en su atención del <strong>{fecha}</strong>
        con <strong>{profesional_nombre}</strong>:</p>
        <ul style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 24px; margin: 16px 0; color: #0f172a;">
            {lista_docs}
        </ul>
        <p>Guarde estos documentos como respaldo de su atención médica.</p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile<br/>
            contacto@icarticular.cl
        </p>
    </div>
    """

    attachments = [
        {
            "filename": nombre,
            "content":  base64.b64encode(contenido).decode("utf-8")
        }
        for nombre, contenido in adjuntos
    ]

    try:
        resend.Emails.send({
            "from":        FROM_EMAIL,
            "to":          [email_paciente],
            "subject":     f"ICA — Documentos de su atención · {fecha}",
            "html":        html,
            "attachments": attachments
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL documentos: {e}")
        return False
    

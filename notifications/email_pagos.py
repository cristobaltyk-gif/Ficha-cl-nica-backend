"""
notifications/email_pagos.py
Emails relacionados a confirmación de asistencia y pagos Flow.
"""

import os
import resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL     = "Instituto de Cirugía Articular <contacto@icarticular.cl>"
BACKEND_URL    = os.getenv("BACKEND_URL", "https://services.icarticular.cl")

LOGO_URL = "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300"


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


# ======================================================
# CONFIRMACIÓN DE ASISTENCIA + LINK PAGO
# ======================================================

def enviar_confirmacion_asistencia(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    monto: int,
    es_gratuito: bool,
    token: str
) -> bool:
    _init()

    link = f"{BACKEND_URL}/api/confirmar-asistencia?token={token}"
    monto_str = "Sin costo" if es_gratuito else f"${monto:,}".replace(",", ".")

    pago_html = "" if es_gratuito else f"""
        <p style="margin-top: 12px;">Valor de la consulta: <strong>{monto_str}</strong></p>
        <p style="font-size: 13px; color: #64748b; margin-top: 4px;">
            Al confirmar su asistencia podrá pagar en línea con tarjeta o transferencia.
        </p>
    """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Recuerde su cita de mañana</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Le recordamos que tiene una cita programada para mañana:</p>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            {"<p style='margin: 4px 0; color: #16a34a; font-weight: bold;'>Atención sin costo</p>" if es_gratuito else ""}
        </div>
        {pago_html}
        <p>Por favor confirme su asistencia:</p>
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
        ">✓ Confirmar asistencia</a>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Si no puede asistir, contáctenos a contacto@icarticular.cl<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": f"ICA — Recuerde su cita mañana {fecha} {hora}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL asistencia: {e}")
        return False


# ======================================================
# CONFIRMACIÓN DE PAGO EXITOSO
# ======================================================

def enviar_confirmacion_pago(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    monto: int,
    numero_orden: str
) -> bool:
    _init()

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Pago recibido ✓</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su pago ha sido procesado exitosamente:</p>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha cita:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0;"><strong>Monto pagado:</strong> ${monto:,}".replace(",", ".")</p>
            <p style="margin: 4px 0;"><strong>N° orden:</strong> {numero_orden}</p>
        </div>
        <p>Le esperamos en el Instituto de Cirugía Articular. Por favor llegue 10 minutos antes.</p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": f"ICA — Pago confirmado · {fecha} {hora}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL pago: {e}")
        return False
  

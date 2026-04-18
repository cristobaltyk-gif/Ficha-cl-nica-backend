"""
notifications/email_pagos.py
Emails relacionados a confirmación de asistencia y pagos Flow.
"""

import os
import resend
from datetime import date

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL     = "Instituto de Cirugía Articular <contacto@icarticular.cl>"
BACKEND_URL    = os.getenv("BACKEND_URL", "https://services.icarticular.cl")

LOGO_URL = "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300"

DIAS_ES   = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES  = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


def _formato_fecha_legible(fecha_iso: str) -> str:
    """
    Convierte "2026-04-13" → "lunes 13 de abril"
    Nunca dice "mañana" — siempre muestra el día real.
    """
    try:
        d = date.fromisoformat(fecha_iso)
        dia_semana = DIAS_ES[d.weekday()]
        mes        = MESES_ES[d.month - 1]
        return f"{dia_semana} {d.day} de {mes}"
    except Exception:
        return fecha_iso


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

    link       = f"{BACKEND_URL}/api/confirmar-asistencia?token={token}"
    monto_str  = "Sin costo" if es_gratuito else f"${monto:,}".replace(",", ".")
    fecha_text = _formato_fecha_legible(fecha)

    pago_html = "" if es_gratuito else f"""
        <p style="margin-top: 12px;">Valor de la consulta: <strong>{monto_str}</strong></p>
        <p style="font-size: 13px; color: #64748b; margin-top: 4px;">
            Al confirmar su asistencia podrá pagar en línea con tarjeta o transferencia.
        </p>
    """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Recuerde su cita del {fecha_text}</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Le recordamos que tiene una cita programada para el <strong>{fecha_text}</strong>:</p>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha_text}</p>
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
            "subject": f"ICA — Recuerde su cita del {fecha_text} · {hora}",
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

    fecha_text = _formato_fecha_legible(fecha)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Pago recibido ✓</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su pago ha sido procesado exitosamente:</p>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha cita:</strong> {fecha_text}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0;"><strong>Monto pagado:</strong> ${monto:,}</p>
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
            "subject": f"ICA — Pago confirmado · {fecha_text} {hora}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL pago: {e}")
        return False
    
# ======================================================
# CONFIRMACIÓN DE ASISTENCIA CON LINK PAGO OPCIONAL
# ======================================================

def enviar_asistencia_confirmada(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    monto: int,
    es_gratuito: bool,
    payment_url: str | None = None,
) -> bool:
    _init()

    fecha_text = _formato_fecha_legible(fecha)
    monto_str  = f"${monto:,}".replace(",", ".")

    if es_gratuito:
        pago_html = "<p style='color:#16a34a;font-weight:bold;margin-top:12px;'>Esta atención no tiene costo para usted.</p>"
    elif payment_url:
        pago_html = f"""
        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;
                    padding:16px 18px;margin:20px 0;">
            <p style="margin:0 0 6px 0;font-size:14px;color:#78350f;">
                💳 Valor de la consulta: <strong>{monto_str}</strong>
            </p>
            <p style="margin:0 0 12px 0;font-size:13px;color:#92400e;">
                Si desea puede pagar en línea ahora con tarjeta o transferencia:
            </p>
            <a href="{payment_url}" style="display:inline-block;background:#d97706;
                color:white;padding:11px 24px;border-radius:8px;
                text-decoration:none;font-weight:bold;font-size:14px;">
                Pagar en línea →
            </a>
            <p style="margin:10px 0 0 0;font-size:11px;color:#92400e;">
                El pago es opcional. También puede cancelar en el centro el día de su consulta.
            </p>
        </div>
        """
    else:
        pago_html = f"<p style='font-size:13px;color:#64748b;margin-top:12px;'>Valor consulta: <strong>{monto_str}</strong>. Puede cancelar en el centro.</p>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height:60px;margin-bottom:24px;"/>
        <h2 style="color:#166534;">✓ Asistencia confirmada</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su asistencia ha sido registrada exitosamente:</p>
        <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:16px;margin:20px 0;">
            <p style="margin:4px 0;"><strong>Fecha:</strong> {fecha_text}</p>
            <p style="margin:4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin:4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
        </div>
        {pago_html}
        <p style="margin-top:16px;">Le esperamos 10 minutos antes de su hora.</p>
        <p style="color:#64748b;font-size:12px;margin-top:24px;">
            Si no puede asistir, contáctenos a contacto@icarticular.cl<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_paciente],
            "subject": f"ICA — Asistencia confirmada · {fecha_text} {hora}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL asistencia confirmada: {e}")
        return False

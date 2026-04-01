"""
notifications/email_service.py
"""

import os
import resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL     = "Instituto de Cirugía Articular <contacto@icarticular.cl>"
BACKEND_URL    = os.getenv("BACKEND_URL", "https://services.icarticular.cl")


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


# ======================================================
# 1. CONFIRMACIÓN DE CONTROL GRATUITO
# ======================================================

def enviar_confirmacion_gratuito(
    *,
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional: str,
    token: str
) -> bool:
    _init()

    # Link apunta directo al backend — confirma y muestra HTML al paciente
    link = f"{BACKEND_URL}/api/control/confirmar?token={token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #0f172a;">Confirmación de atención sin costo</h2>

        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>

        <p>Le informamos que su próxima atención en el Instituto de Cirugía Articular
        ha sido marcada como <strong>control gratuito</strong>:</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha}</p>
            <p style="margin: 4px 0;"><strong>Hora:</strong> {hora}</p>
            <p style="margin: 4px 0; color: #16a34a; font-weight: bold;">Esta atención no tiene costo para usted.</p>
        </div>

        <p>Por favor confirme que ha recibido esta información haciendo click en el botón:</p>

        <a href="{link}" style="
            display: inline-block;
            background: #0f172a;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            margin: 16px 0;
        ">Confirmar atención gratuita</a>

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
# 2. ENVÍO DE PDF
# ======================================================

def enviar_pdf_paciente(
    *,
    email_paciente: str,
    nombre_paciente: str,
    tipo_documento: str,
    pdf_bytes: bytes,
    nombre_archivo: str,
    fecha: str,
    profesional: str
) -> bool:
    _init()

    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #0f172a;">Documento clínico — {tipo_documento}</h2>

        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>

        <p>Adjunto encontrará su <strong>{tipo_documento}</strong> generado el {fecha}
        en el Instituto de Cirugía Articular.</p>

        <p>Guarde este documento como respaldo de su atención médica.</p>

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile<br/>
            contacto@icarticular.cl
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":        FROM_EMAIL,
            "to":          [email_paciente],
            "subject":     f"ICA — {tipo_documento} · {fecha}",
            "html":        html,
            "attachments": [{
                "filename": nombre_archivo,
                "content":  pdf_b64
            }]
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL PDF: {e}")
        return False
    

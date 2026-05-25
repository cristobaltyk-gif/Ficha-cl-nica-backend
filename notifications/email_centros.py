"""
notifications/email_centros.py
Correos de telemedicina configurables por scope/centro.

Ahora apunta a ICA para pruebas.
Cuando se agregue un centro externo, agregar su entrada en CENTROS_CONFIG
con su propio from_email, nombre, logo y color.
"""

import os
import resend
from datetime import date

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
BACKEND_URL    = os.getenv("BACKEND_URL", "https://services.icarticular.cl")

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN POR CENTRO/SCOPE
# Para agregar un centro externo, agregar su entrada aquí.
# ══════════════════════════════════════════════════════════════

CENTROS_CONFIG: dict = {
    "ica": {
        "from_email": "Instituto de Cirugía Articular <contacto@icarticular.cl>",
        "nombre":     "Instituto de Cirugía Articular",
        "logo":       "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300",
        "color":      "#0f172a",
        "color_badge_bg":     "#eff6ff",
        "color_badge_border": "#bfdbfe",
        "contacto":   "contacto@icarticular.cl",
        "ciudad":     "Curicó, Chile",
    },
    # "dermatologo_xyz": {
    #     "from_email": "Centro Dermatológico XYZ <contacto@xyz.cl>",
    #     "nombre":     "Centro Dermatológico XYZ",
    #     "logo":       "https://...",
    #     "color":      "#1d4ed8",
    #     "color_badge_bg":     "#f0fdf4",
    #     "color_badge_border": "#86efac",
    #     "contacto":   "contacto@xyz.cl",
    #     "ciudad":     "Santiago, Chile",
    # },
}

DIAS_ES  = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


def _get_centro(scope: str) -> dict:
    return CENTROS_CONFIG.get(scope, CENTROS_CONFIG["ica"])


def _formato_fecha(fecha_iso: str) -> str:
    try:
        d = date.fromisoformat(fecha_iso)
        return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}"
    except Exception:
        return fecha_iso


# ══════════════════════════════════════════════════════════════
# 1. RESERVA TELEMEDICINA + LINK PAGO FLOW
# Se envía al reservar — lleva el pago directo, no "confirmar asistencia"
# ══════════════════════════════════════════════════════════════

def enviar_reserva_telemedicina(
    *,
    scope: str = "ica",
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    monto: int,
    payment_url: str,
) -> bool:
    _init()
    centro     = _get_centro(scope)
    fecha_text = _formato_fecha(fecha)
    monto_str  = f"${monto:,}".replace(",", ".")

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                padding: 24px; background: #fff;">
        <img src="{centro['logo']}" alt="{centro['nombre']}"
             style="height: 60px; margin-bottom: 24px;" />

        <h2 style="color: {centro['color']};">Consulta de telemedicina reservada</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su consulta de telemedicina ha sido registrada exitosamente:</p>

        <div style="background: {centro['color_badge_bg']};
                    border: 1px solid {centro['color_badge_border']};
                    border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Fecha:</strong> {fecha_text}</p>
            <p style="margin: 4px 0;"><strong>Hora límite de respuesta:</strong> {hora}</p>
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0;"><strong>Modalidad:</strong> Telemedicina — consulta por imágenes</p>
        </div>

        <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
                    padding: 16px 18px; margin: 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 14px; color: #78350f;">
                💳 Valor de la consulta: <strong>{monto_str}</strong>
            </p>
            <p style="margin: 0 0 12px 0; font-size: 13px; color: #92400e;">
                Para que su consulta sea procesada, complete el pago en línea:
            </p>
            <a href="{payment_url}"
               style="display: inline-block; background: #d97706; color: white;
                      padding: 12px 24px; border-radius: 8px; text-decoration: none;
                      font-weight: bold; font-size: 14px;">
                Pagar consulta →
            </a>
            <p style="margin: 10px 0 0 0; font-size: 11px; color: #92400e;">
                Su consulta será revisada por el médico una vez confirmado el pago.
            </p>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
                    padding: 14px 16px; margin: 20px 0;">
            <p style="margin: 0 0 6px 0; font-weight: bold; color: #0f172a; font-size: 13px;">
                📸 ¿Cómo funciona?
            </p>
            <ol style="margin: 0; padding-left: 18px; font-size: 13px;
                       color: #475569; line-height: 1.8;">
                <li>Usted ya subió sus imágenes al reservar</li>
                <li>Complete el pago haciendo clic en el botón</li>
                <li>El médico revisará sus imágenes y enviará su informe por correo</li>
            </ol>
        </div>

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Si tiene dudas contáctenos a
            <a href="mailto:{centro['contacto']}">{centro['contacto']}</a><br/>
            {centro['nombre']} — {centro['ciudad']}
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    centro["from_email"],
            "to":      [email_paciente],
            "subject": f"Consulta telemedicina · {fecha_text} — Pago pendiente",
            "html":    html,
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL telemedicina reserva [{scope}]: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# 2. CONFIRMACIÓN DE PAGO TELEMEDICINA
# Se envía desde el webhook Flow cuando el pago es exitoso
# ══════════════════════════════════════════════════════════════

def enviar_pago_telemedicina(
    *,
    scope: str = "ica",
    email_paciente: str,
    nombre_paciente: str,
    fecha: str,
    hora: str,
    profesional_nombre: str,
    monto: int,
    numero_orden: str,
) -> bool:
    _init()
    centro     = _get_centro(scope)
    fecha_text = _formato_fecha(fecha)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                padding: 24px; background: #fff;">
        <img src="{centro['logo']}" alt="{centro['nombre']}"
             style="height: 60px; margin-bottom: 24px;" />

        <h2 style="color: #166534;">✓ Pago recibido — Consulta en proceso</h2>
        <p>Estimado/a <strong>{nombre_paciente}</strong>,</p>
        <p>Su pago ha sido confirmado y su consulta de telemedicina está siendo procesada:</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac;
                    border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Profesional:</strong> {profesional_nombre}</p>
            <p style="margin: 4px 0;"><strong>Fecha consulta:</strong> {fecha_text}</p>
            <p style="margin: 4px 0;"><strong>Monto pagado:</strong> ${monto:,}</p>
            <p style="margin: 4px 0;"><strong>N° orden:</strong> {numero_orden}</p>
        </div>

        <p>El médico revisará sus imágenes y le enviará el informe a este correo.</p>

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Si tiene dudas contáctenos a
            <a href="mailto:{centro['contacto']}">{centro['contacto']}</a><br/>
            {centro['nombre']} — {centro['ciudad']}
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from":    centro["from_email"],
            "to":      [email_paciente],
            "subject": f"Consulta telemedicina confirmada · {fecha_text}",
            "html":    html,
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL pago telemedicina [{scope}]: {e}")
        return False

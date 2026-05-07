"""
notifications/email_suscripciones.py
Emails relacionados a suscripciones de centros clínicos.
"""
from __future__ import annotations

import os
import resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL     = "Instituto de Cirugía Articular <contacto@icarticular.cl>"
LOGO_URL       = "https://lh3.googleusercontent.com/sitesv/APaQ0SSMBWniO2NWVDwGoaCaQjiel3lBKrmNgpaZZY-ZsYzTawYaf-_7Ad-xfeKVyfCqxa7WgzhWPKHtdaCS0jGtFRrcseP-R8KG1LfY2iYuhZeClvWEBljPLh9KANIClyKSsiSJH8_of4LPUOJUl7cWNwB2HKR7RVH_xB_h9BG-8Nr9jnorb-q2gId2=w300"
CLINICA_URL    = "https://clinica.icarticular.cl"


def _init():
    if not RESEND_API_KEY:
        raise RuntimeError("Falta variable RESEND_API_KEY")
    resend.api_key = RESEND_API_KEY


def _fmt(n: int) -> str:
    return f"${n:,}".replace(",", ".")


# ══════════════════════════════════════════════════════════════
# 1. PRIMER PAGO — link de pago al suscribir
# ══════════════════════════════════════════════════════════════

def enviar_link_primer_pago(
    *,
    email_contacto: str,
    nombre_centro:  str,
    monto:          int,
    link_pago:      str,
    fecha_vencimiento: str,
) -> bool:
    _init()
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #0f172a;">Bienvenido/a al sistema clínico ICA 🎉</h2>
        <p>Estimado/a administrador/a de <strong>{nombre_centro}</strong>,</p>
        <p>Su suscripción ha sido creada exitosamente. Para activar su acceso al sistema,
        complete el primer pago:</p>
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
                    padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Centro:</strong> {nombre_centro}</p>
            <p style="margin: 4px 0;"><strong>Monto mensual:</strong> {_fmt(monto)}</p>
            <p style="margin: 4px 0;"><strong>Vencimiento:</strong> {fecha_vencimiento}</p>
        </div>
        <a href="{link_pago}" style="display: inline-block; background: #1e3a8a; color: white;
            padding: 14px 28px; border-radius: 8px; text-decoration: none;
            font-weight: bold; font-size: 15px; margin: 20px 0;">
            💳 Realizar primer pago →
        </a>
        <p style="font-size: 13px; color: #64748b; margin-top: 16px;">
            Una vez confirmado el pago, recibirá las credenciales de acceso al sistema.
        </p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile<br/>contacto@icarticular.cl
        </p>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_contacto],
            "subject": f"ICA — Bienvenido/a · Active su suscripción {nombre_centro}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL primer pago: {e}"); return False


# ══════════════════════════════════════════════════════════════
# 2. CREDENCIALES — después de confirmar el pago
# ══════════════════════════════════════════════════════════════

def enviar_credenciales_acceso(
    *,
    email_contacto: str,
    nombre_centro:  str,
    username_admin: str,
    password_temp:  str,
    plan:           str,
    max_usuarios:   dict,
) -> bool:
    _init()

    # Resumen del plan
    plan_rows = ""
    for rol, cantidad in max_usuarios.items():
        plan_rows += f"<tr><td style='padding:6px 12px;text-transform:capitalize'>{rol}</td><td style='padding:6px 12px;font-weight:600'>{cantidad}</td></tr>"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #166534;">✅ Pago confirmado — Credenciales de acceso</h2>
        <p>Estimado/a administrador/a de <strong>{nombre_centro}</strong>,</p>
        <p>Su pago ha sido confirmado. A continuación sus credenciales de acceso al sistema:</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;
                    padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">URL de acceso:</p>
            <p style="margin: 0 0 16px;"><a href="{CLINICA_URL}" style="color: #1e3a8a; font-weight: bold;">{CLINICA_URL}</a></p>
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">Usuario administrador:</p>
            <p style="margin: 0 0 16px; font-size: 18px; font-weight: 800; color: #0f172a; letter-spacing: 1px;">{username_admin}</p>
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">Contraseña temporal:</p>
            <p style="margin: 0; font-size: 18px; font-weight: 800; color: #0f172a; letter-spacing: 2px;">{password_temp}</p>
        </div>

        <p style="color: #dc2626; font-weight: 600; font-size: 13px;">
            ⚠️ Por seguridad, cambie su contraseña al ingresar por primera vez.
        </p>

        <p style="margin-top: 20px; font-weight: 700;">Su plan incluye:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 8px 0 20px;">
            <thead>
                <tr style="background: #1e3a8a; color: white;">
                    <th style="padding: 8px 12px; text-align: left;">Rol</th>
                    <th style="padding: 8px 12px; text-align: left;">Usuarios</th>
                </tr>
            </thead>
            <tbody style="background: #f8fafc;">
                {plan_rows}
            </tbody>
        </table>

        <p style="font-size: 13px; color: #475569;">
            Con su usuario administrador podrá crear los usuarios de su equipo
            dentro de los límites de su plan desde el módulo <strong>Equipo</strong>.
        </p>

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Cualquier consulta: contacto@icarticular.cl<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_contacto],
            "subject": f"ICA — Credenciales de acceso · {nombre_centro}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL credenciales: {e}"); return False


# ══════════════════════════════════════════════════════════════
# 3. RECORDATORIO 3 DÍAS ANTES
# ══════════════════════════════════════════════════════════════

def enviar_recordatorio_renovacion(
    *,
    email_contacto:    str,
    nombre_centro:     str,
    monto:             int,
    fecha_vencimiento: str,
    link_pago:         str,
) -> bool:
    _init()
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #f97316;">⏰ Su suscripción vence en 3 días</h2>
        <p>Estimado/a administrador/a de <strong>{nombre_centro}</strong>,</p>
        <p>Su suscripción al sistema clínico ICA vence el <strong>{fecha_vencimiento}</strong>.</p>
        <div style="background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px;
                    padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Monto:</strong> {_fmt(monto)}/mes</p>
            <p style="margin: 4px 0;"><strong>Vencimiento:</strong> {fecha_vencimiento}</p>
        </div>
        <a href="{link_pago}" style="display: inline-block; background: #f97316; color: white;
            padding: 14px 28px; border-radius: 8px; text-decoration: none;
            font-weight: bold; font-size: 15px; margin: 20px 0;">
            🔄 Renovar ahora →
        </a>
        <p style="font-size: 13px; color: #64748b;">
            Si no renueva, su acceso será suspendido automáticamente al vencer.
        </p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Instituto de Cirugía Articular — Curicó, Chile<br/>contacto@icarticular.cl
        </p>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_contacto],
            "subject": f"ICA — Renueve su suscripción · {nombre_centro} vence el {fecha_vencimiento}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL recordatorio: {e}"); return False


# ══════════════════════════════════════════════════════════════
# 4. SUSPENSIÓN POR NO PAGO
# ══════════════════════════════════════════════════════════════

def enviar_aviso_suspension(
    *,
    email_contacto: str,
    nombre_centro:  str,
    monto:          int,
) -> bool:
    _init()
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #dc2626;">⚠️ Acceso suspendido por falta de pago</h2>
        <p>Estimado/a administrador/a de <strong>{nombre_centro}</strong>,</p>
        <p>Su suscripción ha vencido y el acceso al sistema ha sido <strong>suspendido</strong>.</p>
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;
                    padding: 16px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Monto pendiente:</strong> {_fmt(monto)}/mes</p>
        </div>
        <p>Para reactivar su acceso, contáctenos a:</p>
        <p><a href="mailto:contacto@icarticular.cl" style="color: #1e3a8a; font-weight: bold;">
            contacto@icarticular.cl
        </a></p>
        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Sus datos están seguros y serán preservados durante 30 días.<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_contacto],
            "subject": f"ICA — Acceso suspendido · {nombre_centro}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL suspensión: {e}"); return False


# ══════════════════════════════════════════════════════════════
# 5. CREDENCIALES EXTERNO — acceso individual
# ══════════════════════════════════════════════════════════════

def enviar_credenciales_externo(
    *,
    email_contacto: str,
    nombre:         str,
    username:       str,
    password_temp:  str,
    plan:           str,
) -> bool:
    _init()
    planes = {
        "externo_base":     "Externo Base — acceso a sus propios pacientes",
        "externo_completo": "Externo Completo — acceso completo + contabilidad",
    }
    plan_label = planes.get(plan, plan)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #fff;">
        <img src="{LOGO_URL}" alt="ICA" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #166534;">✅ Pago confirmado — Acceso activado</h2>
        <p>Estimado/a <strong>{nombre}</strong>,</p>
        <p>Su pago ha sido confirmado. A continuación sus credenciales de acceso al sistema clínico:</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px;
                    padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">URL de acceso:</p>
            <p style="margin: 0 0 16px;">
                <a href="{CLINICA_URL}" style="color: #1e3a8a; font-weight: bold;">{CLINICA_URL}</a>
            </p>
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">Usuario:</p>
            <p style="margin: 0 0 16px; font-size: 18px; font-weight: 800; color: #0f172a; letter-spacing: 1px;">{username}</p>
            <p style="margin: 0 0 8px; font-size: 13px; color: #475569;">Contraseña temporal:</p>
            <p style="margin: 0; font-size: 18px; font-weight: 800; color: #0f172a; letter-spacing: 2px;">{password_temp}</p>
        </div>

        <p style="color: #dc2626; font-weight: 600; font-size: 13px;">
            ⚠️ Por seguridad, cambie su contraseña al ingresar por primera vez.
        </p>

        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
                    padding: 14px; margin: 16px 0; font-size: 13px; color: #1e40af;">
            <strong>Plan activo:</strong> {plan_label}
        </div>

        <p style="color: #64748b; font-size: 12px; margin-top: 24px;">
            Cualquier consulta: contacto@icarticular.cl<br/>
            Instituto de Cirugía Articular — Curicó, Chile
        </p>
    </div>
    """
    try:
        resend.Emails.send({
            "from":    FROM_EMAIL,
            "to":      [email_contacto],
            "subject": f"ICA — Acceso activado · Bienvenido/a {nombre}",
            "html":    html
        })
        return True
    except Exception as e:
        print(f"❌ ERROR EMAIL credenciales externo: {e}"); return False

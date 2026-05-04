"""
modules/suscripciones/suscripcion_scheduler.py
Revisa vencimientos diariamente y envía recordatorios.
"""
from __future__ import annotations

import threading
from datetime import date, timedelta
from db.supabase_client import get_all_suscripciones, update_suscripcion


def _revisar_suscripciones():
    hoy = date.today().isoformat()
    alerta = (date.today() + timedelta(days=3)).isoformat()

    try:
        suscripciones = get_all_suscripciones()
    except Exception as e:
        print(f"[SUSCRIPCIONES] Error leyendo BD: {e}")
        return

    for s in suscripciones:
        centro_id  = s["centro_id"]
        vencimiento = s.get("fecha_vencimiento", "")
        estado      = s.get("estado", "activo")

        # Verificar descuento vencido
        if s.get("descuento_hasta") and hoy > s["descuento_hasta"]:
            update_suscripcion(centro_id, {
                "descuento_pct": 0, "descuento_motivo": "",
                "descuento_hasta": None, "precio_final": s["precio_base"]
            })
            print(f"[SUSCRIPCIONES] Descuento vencido para {centro_id}")

        # Vencida → desactivar
        if estado == "activo" and vencimiento and hoy > vencimiento:
            update_suscripcion(centro_id, {"estado": "vencido"})
            print(f"[SUSCRIPCIONES] ⚠️ Vencida: {centro_id}")
            try:
                _notificar_vencimiento(s)
            except Exception as e:
                print(f"[SUSCRIPCIONES] Error notificando vencimiento: {e}")

        # Próxima a vencer → recordatorio
        elif estado == "activo" and vencimiento == alerta:
            print(f"[SUSCRIPCIONES] 📧 Recordatorio 3 días: {centro_id}")
            try:
                _notificar_recordatorio(s)
            except Exception as e:
                print(f"[SUSCRIPCIONES] Error notificando recordatorio: {e}")


def _notificar_vencimiento(s: dict):
    from notifications.email_service import _init, FROM_EMAIL, LOGO_URL
    import resend
    _init()

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <img src="{LOGO_URL}" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #dc2626;">Suscripción vencida</h2>
        <p>Estimado/a administrador/a de <strong>{s['nombre_centro']}</strong>,</p>
        <p>Su suscripción al sistema clínico ha <strong>vencido</strong>.</p>
        <p>Para reactivar el acceso, realice el pago de <strong>${s['precio_final']:,}</strong>/mes.</p>
        <p>Contáctenos a <a href="mailto:contacto@icarticular.cl">contacto@icarticular.cl</a></p>
    </div>
    """
    resend.Emails.send({
        "from": FROM_EMAIL, "to": [s["email_contacto"]],
        "subject": f"Suscripción vencida — {s['nombre_centro']}",
        "html": html
    })


def _notificar_recordatorio(s: dict):
    from notifications.email_service import _init, FROM_EMAIL, LOGO_URL
    import resend
    _init()

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
        <img src="{LOGO_URL}" style="height: 60px; margin-bottom: 24px;" />
        <h2 style="color: #f97316;">Recordatorio de pago</h2>
        <p>Estimado/a administrador/a de <strong>{s['nombre_centro']}</strong>,</p>
        <p>Su suscripción vence en <strong>3 días</strong> ({s['fecha_vencimiento']}).</p>
        <p>Monto a pagar: <strong>${s['precio_final']:,}/mes</strong></p>
        <p>Para renovar automáticamente, asegúrese de tener su tarjeta registrada.</p>
        <p>Contáctenos a <a href="mailto:contacto@icarticular.cl">contacto@icarticular.cl</a></p>
    </div>
    """
    resend.Emails.send({
        "from": FROM_EMAIL, "to": [s["email_contacto"]],
        "subject": f"Renovación próxima — {s['nombre_centro']}",
        "html": html
    })


def start_suscripcion_scheduler():
    import schedule, time

    schedule.every().day.at("08:00").do(_revisar_suscripciones)

    def run():
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    print("🔔 [SUSCRIPCIONES] Scheduler iniciado — revisa diariamente a las 08:00")
  

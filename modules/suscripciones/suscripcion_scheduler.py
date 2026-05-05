"""
modules/suscripciones/suscripcion_scheduler.py
Revisa vencimientos diariamente y envía recordatorios.
"""
from __future__ import annotations

import os
import threading
from datetime import date, timedelta
from db.supabase_client import get_all_suscripciones, update_suscripcion

BACKEND_URL  = os.getenv("BACKEND_URL",  "https://services.icarticular.cl")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://admin.icarticular.cl")


def _generar_link_renovacion(s: dict) -> str:
    """Genera link de pago Flow para renovación mensual."""
    try:
        from modules.pagos.flow_client import crear_pago
        mes    = date.today().strftime("%Y-%m")
        result = crear_pago(
            id_pago=f"SUB-{s['centro_id']}-{mes}",
            amount=s["precio_final"],
            subject=f"Renovación {s['nombre_centro']} — {mes}",
            email=s["email_contacto"],
            url_confirmation=f"{BACKEND_URL}/api/suscripciones/webhook/pago",
            url_return=f"{FRONTEND_URL}/suscripciones",
            optional_data={"centro_id": s["centro_id"]},
        )
        return f"{result['url']}?token={result['token']}"
    except Exception as e:
        print(f"[SUSCRIPCIONES] Error generando link Flow: {e}")
        return ""


def _revisar_suscripciones():
    hoy    = date.today().isoformat()
    alerta = (date.today() + timedelta(days=3)).isoformat()

    print(f"[SUSCRIPCIONES] Revisando {hoy}…")

    try:
        suscripciones = get_all_suscripciones()
    except Exception as e:
        print(f"[SUSCRIPCIONES] Error leyendo BD: {e}")
        return

    for s in suscripciones:
        centro_id   = s["centro_id"]
        vencimiento = s.get("fecha_vencimiento", "")
        estado      = s.get("estado", "activo")

        # ── Descuento vencido ────────────────────────────────
        if s.get("descuento_hasta") and hoy > s["descuento_hasta"]:
            update_suscripcion(centro_id, {
                "descuento_pct":   0,
                "descuento_motivo": "",
                "descuento_hasta": None,
                "precio_final":    s["precio_base"]
            })
            print(f"[SUSCRIPCIONES] Descuento vencido para {centro_id}")

        # ── Vencida → suspender y notificar ─────────────────
        if estado == "activo" and vencimiento and hoy > vencimiento:
            update_suscripcion(centro_id, {"estado": "suspendido"})
            print(f"[SUSCRIPCIONES] ⚠️ Suspendida: {centro_id}")
            try:
                from notifications.email_suscripciones import enviar_aviso_suspension
                enviar_aviso_suspension(
                    email_contacto=s["email_contacto"],
                    nombre_centro=s["nombre_centro"],
                    monto=s["precio_final"],
                )
                # Desactivar usuarios del centro
                _suspender_usuarios_centro(centro_id)
            except Exception as e:
                print(f"[SUSCRIPCIONES] Error suspendiendo {centro_id}: {e}")

        # ── 3 días antes → recordatorio con link de pago ────
        elif estado == "activo" and vencimiento == alerta:
            print(f"[SUSCRIPCIONES] 📧 Recordatorio 3 días: {centro_id}")
            try:
                link = _generar_link_renovacion(s)
                from notifications.email_suscripciones import enviar_recordatorio_renovacion
                enviar_recordatorio_renovacion(
                    email_contacto=s["email_contacto"],
                    nombre_centro=s["nombre_centro"],
                    monto=s["precio_final"],
                    fecha_vencimiento=vencimiento,
                    link_pago=link,
                )
            except Exception as e:
                print(f"[SUSCRIPCIONES] Error recordatorio {centro_id}: {e}")


def _suspender_usuarios_centro(centro_id: str):
    """Desactiva todos los usuarios del centro al suspender."""
    try:
        from db.supabase_client import _get_conn
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE usuarios SET active = FALSE
                    WHERE role->>'scope' = %s
                """, (centro_id,))
                count = cur.rowcount
                conn.commit()
        print(f"[SUSCRIPCIONES] {count} usuarios desactivados para {centro_id}")
    except Exception as e:
        print(f"[SUSCRIPCIONES] Error desactivando usuarios: {e}")


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
    

"""
modules/pagos/scheduler.py
Envía correos de confirmación de asistencia a las 12:00 del día anterior.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TOKENS_PATH = Path("/data/confirmacion_tokens.json")
CHILE_TZ    = ZoneInfo("America/Santiago")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_professional_name(professional_id: str) -> str:
    from db.supabase_client import get_profesionales
    profs = get_profesionales()
    return profs.get(professional_id, {}).get("name", professional_id)


def _get_caja_config() -> dict:
    from db.supabase_client import get_caja_config
    config = get_caja_config()
    return config if config else {"particular": 45000, "control_costo": 45000, "sobrecupo": 45000, "kinesiologia": 25000}


def _target_date(hoy: date) -> date | None:
    weekday = hoy.weekday()
    if weekday == 6: return None
    if weekday == 4: return hoy + timedelta(days=3)
    if weekday == 5: return hoy + timedelta(days=2)
    return hoy + timedelta(days=1)


def enviar_confirmaciones_dia(target: date) -> int:
    from notifications.email_pagos import enviar_confirmacion_asistencia
    from agenda.store import read_day

    tokens     = _load_json(TOKENS_PATH)
    config     = _get_caja_config()
    target_str = target.isoformat()
    day_data   = read_day(target_str)
    enviados   = 0

    for professional, prof_data in day_data.items():
        slots       = prof_data.get("slots", {})
        nombre_prof = _get_professional_name(professional)

        for time_str, slot in slots.items():
            if slot.get("status") not in ("reserved", "confirmed"):
                continue
            if slot.get("asistencia_confirmada") or slot.get("confirmacion_enviada"):
                continue

            rut = slot.get("rut")
            if not rut:
                continue

            from db.supabase_client import get_paciente
            admin = get_paciente(rut)
            if not admin:
                continue

            email = admin.get("email", "").strip()
            if not email:
                continue

            nombre      = f"{admin.get('nombre','')} {admin.get('apellido_paterno','')}".strip()
            tipo        = slot.get("tipo_atencion", "particular")
            es_gratuito = tipo in ("control_gratuito", "cortesia")
            monto       = 0 if es_gratuito else config.get(tipo, 0)

            token = secrets.token_urlsafe(32)
            tokens[token] = {
                "date":          target_str,
                "time":          time_str,
                "professional":  professional,
                "rut":           rut,
                "email":         email,
                "monto":         monto,
                "tipo_atencion": tipo,
                "created_at":    datetime.now(CHILE_TZ).isoformat()
            }

            try:
                ok = enviar_confirmacion_asistencia(
                    email_paciente=email,
                    nombre_paciente=nombre,
                    fecha=target_str,
                    hora=time_str,
                    profesional_nombre=nombre_prof,
                    monto=monto,
                    es_gratuito=es_gratuito,
                    token=token
                )
                if ok:
                    # Marcar confirmacion_enviada en el slot
                    from agenda.store import set_slot
                    slot["confirmacion_enviada"] = True
                    set_slot(
                        date=target_str, time=time_str,
                        professional=professional,
                        status=slot.get("status", "reserved"),
                        rut=rut,
                        extra={**{k:v for k,v in slot.items() if k not in ("status","rut")}}
                    )
                    enviados += 1
                    print(f"✅ Confirmación enviada: {rut} · {target_str} {time_str}")
                else:
                    del tokens[token]
            except Exception as e:
                print(f"❌ Error enviando confirmación {rut}: {e}")
                tokens.pop(token, None)

    _save_json(TOKENS_PATH, tokens)
    return enviados


def _loop():
    print("🕐 Scheduler confirmaciones iniciado")
    ultimo = None

    while True:
        ahora = datetime.now(CHILE_TZ)
        hoy   = ahora.date()

        if ahora.hour == 12 and ahora.minute < 5 and ultimo != hoy:
            target = _target_date(hoy)
            if target:
                print(f"📧 Enviando confirmaciones para {target}…")
                try:
                    n = enviar_confirmaciones_dia(target)
                    print(f"✅ {n} confirmaciones enviadas para {target}")
                except Exception as e:
                    print(f"❌ Error scheduler: {e}")
            ultimo = hoy

        time.sleep(60)


def start_scheduler():
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("🚀 Scheduler iniciado")
    

"""
modules/pagos/scheduler.py
Envía correos de confirmación de asistencia a las 12:00 del día anterior.

Lógica:
- Lunes–jueves  → envía para el día siguiente
- Viernes       → envía para el lunes
- Sábado        → envía para el lunes
- Domingo       → no envía
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AGENDA_PATH        = Path("/data/agenda_future.json")
PACIENTES_PATH     = Path("/data/pacientes")
PROFESSIONALS_PATH = Path("/data/professionals.json")
TOKENS_PATH        = Path("/data/confirmacion_tokens.json")

CHILE_TZ = ZoneInfo("America/Santiago")


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
    data = _load_json(PROFESSIONALS_PATH)
    return data.get(professional_id, {}).get("name", professional_id)


def _get_caja_config() -> dict:
    import os
    for root, dirs, files in os.walk("/opt/render/project/src"):
        for f in files:
            if f == "caja_config.json":
                try:
                    with open(os.path.join(root, f)) as fp:
                        return json.load(fp)
                except:
                    pass
    return {"particular": 45000, "control_costo": 45000, "sobrecupo": 45000, "kinesiologia": 25000}


def _target_date(hoy: date) -> date | None:
    weekday = hoy.weekday()  # 0=lunes … 6=domingo
    if weekday == 6:   return None          # domingo
    if weekday == 4:   return hoy + timedelta(days=3)  # viernes → lunes
    if weekday == 5:   return hoy + timedelta(days=2)  # sábado → lunes
    return hoy + timedelta(days=1)                     # lunes–jueves


def enviar_confirmaciones_dia(target: date) -> int:
    from notifications.email_pagos import enviar_confirmacion_asistencia

    agenda  = _load_json(AGENDA_PATH)
    tokens  = _load_json(TOKENS_PATH)
    config  = _get_caja_config()

    target_str = target.isoformat()
    day_data   = agenda.get("calendar", {}).get(target_str, {})
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

            admin_path = PACIENTES_PATH / rut / "admin.json"
            if not admin_path.exists():
                continue

            with open(admin_path, "r", encoding="utf-8") as f:
                admin = json.load(f)

            email = admin.get("email", "").strip()
            if not email:
                continue

            nombre      = f"{admin.get('nombre','')} {admin.get('apellido_paterno','')}".strip()
            tipo        = slot.get("tipo_atencion", "particular")
            es_gratuito = tipo in ("control_gratuito", "cortesia")
            monto       = 0 if es_gratuito else config.get(tipo, 0)

            token = secrets.token_urlsafe(32)
            tokens[token] = {
                "date":         target_str,
                "time":         time_str,
                "professional": professional,
                "rut":          rut,
                "email":        email,
                "monto":        monto,
                "tipo_atencion": tipo,
                "created_at":   datetime.now(CHILE_TZ).isoformat()
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
                    slot["confirmacion_enviada"] = True
                    enviados += 1
                    print(f"✅ Confirmación enviada: {rut} · {target_str} {time_str}")
                else:
                    del tokens[token]
            except Exception as e:
                print(f"❌ Error enviando confirmación {rut}: {e}")
                tokens.pop(token, None)

    _save_json(AGENDA_PATH, agenda)
    _save_json(TOKENS_PATH, tokens)
    return enviados


def _loop():
    print("🕐 Scheduler confirmaciones iniciado")
    ultimo = None

    while True:
        ahora  = datetime.now(CHILE_TZ)
        hoy    = ahora.date()

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
  

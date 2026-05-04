"""
db/supabase_client.py
"""
from __future__ import annotations

import os
import json
import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def _get_conn():
    url = os.environ.get("SUPABASE_DATABASE_URL")
    if not url:
        raise RuntimeError("Falta variable de entorno SUPABASE_DATABASE_URL")
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def init_db():
    sql = (
        "CREATE TABLE IF NOT EXISTS usuarios ("
        "id TEXT PRIMARY KEY, password TEXT DEFAULT '', active BOOLEAN DEFAULT TRUE, "
        "professional TEXT, role JSONB, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS profesionales ("
        "id TEXT PRIMARY KEY, name TEXT NOT NULL, rut TEXT, specialty TEXT, active BOOLEAN DEFAULT TRUE, "
        "schedule JSONB, blocked_dates TEXT[], created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS pacientes ("
        "rut TEXT PRIMARY KEY, nombre TEXT, apellido_paterno TEXT, apellido_materno TEXT, "
        "fecha_nacimiento TEXT, sexo TEXT, email TEXT, telefono TEXT, direccion TEXT, ciudad TEXT, "
        "prevision TEXT, ocupacion TEXT, extra JSONB, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS eventos ("
        "id SERIAL PRIMARY KEY, rut_paciente TEXT NOT NULL REFERENCES pacientes(rut), "
        "professional_id TEXT REFERENCES profesionales(id), fecha_hora TEXT NOT NULL, tipo TEXT, "
        "contenido JSONB NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE INDEX IF NOT EXISTS idx_eventos_rut ON eventos(rut_paciente);"
        "CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha_hora);"

        "CREATE TABLE IF NOT EXISTS sedes ("
        "id TEXT PRIMARY KEY, regiones JSONB, created_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS trabajadores ("
        "id SERIAL PRIMARY KEY, data JSONB NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS gastos ("
        "id SERIAL PRIMARY KEY, periodo TEXT NOT NULL, data JSONB NOT NULL, "
        "created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS comisiones ("
        "id SERIAL PRIMARY KEY, data JSONB NOT NULL, updated_at TIMESTAMPTZ DEFAULT NOW());"

        "CREATE TABLE IF NOT EXISTS slots ("
        "id SERIAL PRIMARY KEY, date TEXT NOT NULL, time TEXT NOT NULL, professional TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'reserved', rut TEXT, extra JSONB DEFAULT '{}', "
        "updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE (date, time, professional));"

        "CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date);"
        "CREATE INDEX IF NOT EXISTS idx_slots_professional ON slots(professional);"
        "CREATE INDEX IF NOT EXISTS idx_slots_date_prof ON slots(date, professional);"
        "CREATE TABLE IF NOT EXISTS caja (id SERIAL PRIMARY KEY, date TEXT NOT NULL, professional TEXT NOT NULL, time TEXT NOT NULL, data JSONB NOT NULL DEFAULT '{}', updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE (date, professional, time));"
        "CREATE TABLE IF NOT EXISTS pagos (id SERIAL PRIMARY KEY, date TEXT NOT NULL, mes TEXT NOT NULL, professional TEXT NOT NULL, time TEXT NOT NULL, data JSONB NOT NULL DEFAULT '{}', updated_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE (date, professional, time));"
        "CREATE INDEX IF NOT EXISTS idx_pagos_mes ON pagos(mes);"
        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, data JSONB NOT NULL DEFAULT '{}', updated_at TIMESTAMPTZ DEFAULT NOW());"
        "CREATE TABLE IF NOT EXISTS audit_log (id SERIAL PRIMARY KEY, usuario TEXT NOT NULL, accion TEXT NOT NULL, rut_paciente TEXT, ip TEXT, detalle TEXT, created_at TIMESTAMPTZ DEFAULT NOW());"
        "CREATE INDEX IF NOT EXISTS idx_audit_rut ON audit_log(rut_paciente);"
        "CREATE INDEX IF NOT EXISTS idx_audit_usuario ON audit_log(usuario);"
        "CREATE TABLE IF NOT EXISTS suscripciones ("
        "centro_id TEXT PRIMARY KEY, nombre_centro TEXT NOT NULL, "
        "plan TEXT NOT NULL DEFAULT 'centro', roles JSONB DEFAULT '{}', "
        "precio_base INTEGER NOT NULL DEFAULT 0, descuento_pct INTEGER NOT NULL DEFAULT 0, "
        "descuento_motivo TEXT DEFAULT '', descuento_hasta TEXT, "
        "precio_final INTEGER NOT NULL DEFAULT 0, estado TEXT NOT NULL DEFAULT 'activo', "
        "fecha_inicio TEXT, fecha_vencimiento TEXT, flow_customer_id TEXT, "
        "flow_subscription_id TEXT, email_contacto TEXT NOT NULL DEFAULT '', "
        "metodo_pago TEXT NOT NULL DEFAULT 'manual', "
        "created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());"
        "CREATE INDEX IF NOT EXISTS idx_suscripciones_estado ON suscripciones(estado);"
        "CREATE INDEX IF NOT EXISTS idx_suscripciones_vencimiento ON suscripciones(fecha_vencimiento);"
    )
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
    print("✅ [DB] Tablas verificadas/creadas correctamente")


def get_paciente(rut: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pacientes WHERE rut = %s", (rut,))
            row = cur.fetchone()
            return dict(row) if row else None


def create_paciente(data: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pacientes (
                    rut, nombre, apellido_paterno, apellido_materno,
                    fecha_nacimiento, sexo, email, telefono,
                    direccion, ciudad, prevision, ocupacion,
                    extra, created_at, updated_at
                ) VALUES (
                    %(rut)s, %(nombre)s, %(apellido_paterno)s, %(apellido_materno)s,
                    %(fecha_nacimiento)s, %(sexo)s, %(email)s, %(telefono)s,
                    %(direccion)s, %(ciudad)s, %(prevision)s, %(ocupacion)s,
                    %(extra)s, %(created_at)s, %(updated_at)s
                ) RETURNING *
            """, {
                "rut": data["rut"], "nombre": data.get("nombre", ""),
                "apellido_paterno": data.get("apellido_paterno", ""),
                "apellido_materno": data.get("apellido_materno", ""),
                "fecha_nacimiento": data.get("fecha_nacimiento", ""),
                "sexo": data.get("sexo", ""), "email": data.get("email", ""),
                "telefono": data.get("telefono", ""), "direccion": data.get("direccion", ""),
                "ciudad": data.get("ciudad", ""), "prevision": data.get("prevision", ""),
                "ocupacion": data.get("ocupacion", ""),
                "extra": json.dumps(data.get("extra", {})),
                "created_at": now, "updated_at": now,
            })
            conn.commit()
            return dict(cur.fetchone())


def update_paciente(rut: str, data: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pacientes SET
                    nombre=%(nombre)s, apellido_paterno=%(apellido_paterno)s,
                    apellido_materno=%(apellido_materno)s, fecha_nacimiento=%(fecha_nacimiento)s,
                    sexo=%(sexo)s, email=%(email)s, telefono=%(telefono)s,
                    direccion=%(direccion)s, ciudad=%(ciudad)s, prevision=%(prevision)s,
                    ocupacion=%(ocupacion)s, extra=%(extra)s, updated_at=%(updated_at)s
                WHERE rut=%(rut)s RETURNING *
            """, {
                "rut": rut, "nombre": data.get("nombre", ""),
                "apellido_paterno": data.get("apellido_paterno", ""),
                "apellido_materno": data.get("apellido_materno", ""),
                "fecha_nacimiento": data.get("fecha_nacimiento", ""),
                "sexo": data.get("sexo", ""), "email": data.get("email", ""),
                "telefono": data.get("telefono", ""), "direccion": data.get("direccion", ""),
                "ciudad": data.get("ciudad", ""), "prevision": data.get("prevision", ""),
                "ocupacion": data.get("ocupacion", ""),
                "extra": json.dumps(data.get("extra", {})), "updated_at": now,
            })
            conn.commit()
            return dict(cur.fetchone())


def search_pacientes(q: str) -> List[Dict[str, Any]]:
    q_lower = f"%{q.lower()}%"
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM pacientes
                WHERE LOWER(rut) LIKE %(q)s OR LOWER(nombre) LIKE %(q)s
                   OR LOWER(apellido_paterno) LIKE %(q)s OR LOWER(apellido_materno) LIKE %(q)s
                ORDER BY apellido_paterno, nombre LIMIT 50
            """, {"q": q_lower})
            return [dict(r) for r in cur.fetchall()]


def get_eventos(rut: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM eventos WHERE rut_paciente = %s ORDER BY fecha_hora DESC", (rut,))
            rows = cur.fetchall()
            result = []
            for row in rows:
                ev = dict(row["contenido"])
                ev["_id"] = row["id"]
                ev["created_at"] = str(row["created_at"])
                result.append(ev)
            return result


def get_eventos_resumen(rut: str) -> List[Dict[str, Any]]:
    return [{
        "fecha": ev.get("fecha"), "hora": ev.get("hora"),
        "diagnostico": ev.get("diagnostico"),
        "professional_name": ev.get("professional_name") or ev.get("professional_user") or ev.get("professional_id") or "",
        "created_at": ev.get("created_at"),
    } for ev in get_eventos(rut)]


def create_evento(rut: str, evento: Dict[str, Any]) -> Dict[str, Any]:
    fecha_hora = f"{evento.get('fecha', '')}_{evento.get('hora', '').replace(':', '-')}"
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM eventos WHERE rut_paciente = %s AND fecha_hora = %s", (rut, fecha_hora))
            if cur.fetchone():
                raise ValueError("Ya existe una atención en esa fecha y hora")
            cur.execute("""
                INSERT INTO eventos (rut_paciente, professional_id, fecha_hora, tipo, contenido, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (rut, evento.get("professional_id"), fecha_hora,
                  evento.get("tipo", "consulta"), json.dumps(evento), now, now))
            conn.commit()
            evento["_id"] = cur.fetchone()["id"]
            return evento


def get_users() -> Dict[str, Any]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios")
            rows = cur.fetchall()
            return {
                row["id"]: {
                    "password": row["password"], "active": row["active"],
                    "professional": row["professional"], "role": row["role"],
                } for row in rows
            }


def save_user(user_id: str, data: Dict[str, Any]) -> None:
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (id, password, active, professional, role, created_at, updated_at)
                VALUES (%(id)s, %(password)s, %(active)s, %(professional)s, %(role)s, %(now)s, %(now)s)
                ON CONFLICT (id) DO UPDATE SET
                    password=EXCLUDED.password, active=EXCLUDED.active,
                    professional=EXCLUDED.professional, role=EXCLUDED.role, updated_at=EXCLUDED.updated_at
            """, {
                "id": user_id, "password": data.get("password", ""),
                "active": data.get("active", True), "professional": data.get("professional"),
                "role": json.dumps(data.get("role", {})), "now": now,
            })
            conn.commit()


def save_users(users: Dict[str, Any]) -> None:
    for user_id, data in users.items():
        save_user(user_id, data)


def load_users() -> Dict[str, Any]:
    return get_users()


def get_profesionales() -> Dict[str, Any]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM profesionales WHERE active = TRUE")
            rows = cur.fetchall()
            return {
                row["id"]: {
                    "id": row["id"], "name": row["name"], "rut": row["rut"],
                    "specialty": row["specialty"], "active": row["active"],
                    "schedule": row["schedule"], "blocked_dates": row["blocked_dates"] or [],
                } for row in rows
            }


def save_profesional(prof_id: str, data: Dict[str, Any]) -> None:
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO profesionales (id, name, rut, specialty, active, schedule, blocked_dates, created_at, updated_at)
                VALUES (%(id)s, %(name)s, %(rut)s, %(specialty)s, %(active)s, %(schedule)s, %(blocked_dates)s, %(now)s, %(now)s)
                ON CONFLICT (id) DO UPDATE SET
                    name=EXCLUDED.name, rut=EXCLUDED.rut, specialty=EXCLUDED.specialty,
                    active=EXCLUDED.active, schedule=EXCLUDED.schedule,
                    blocked_dates=EXCLUDED.blocked_dates, updated_at=EXCLUDED.updated_at
            """, {
                "id": prof_id, "name": data.get("name", ""), "rut": data.get("rut", ""),
                "specialty": data.get("specialty", ""), "active": data.get("active", True),
                "schedule": json.dumps(data.get("schedule", {})),
                "blocked_dates": data.get("blocked_dates", []), "now": now,
            })
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# CAJA
# ══════════════════════════════════════════════════════════════════════════════

def get_caja_slot(date: str, professional: str, time: str) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM caja WHERE date=%s AND professional=%s AND time=%s", (date, professional, time))
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def get_caja_day(date: str, professional: str) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT time, data FROM caja WHERE date=%s AND professional=%s", (date, professional))
            return {row["time"]: dict(row["data"]) for row in cur.fetchall()}

def save_caja_slot(date: str, professional: str, time: str, slot: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO caja (date, professional, time, data, updated_at)
                VALUES (%s,%s,%s,%s,NOW())
                ON CONFLICT (date, professional, time) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (date, professional, time, json.dumps(slot)))
            conn.commit()

def delete_caja_slot(date: str, professional: str, time: str) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM caja WHERE date=%s AND professional=%s AND time=%s", (date, professional, time))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# PAGOS
# ══════════════════════════════════════════════════════════════════════════════

def get_pagos_day(date: str, professional: str) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT time, data FROM pagos WHERE date=%s AND professional=%s", (date, professional))
            return {row["time"]: dict(row["data"]) for row in cur.fetchall()}

def get_pagos_mes(mes: str) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT date, professional, time, data FROM pagos WHERE mes=%s", (mes,))
            return [{**dict(row["data"]), "fecha": row["date"], "time": row["time"], "professional": row["professional"]} for row in cur.fetchall()]

def save_pago(date: str, professional: str, time: str, pago: dict) -> None:
    mes = date[:7]
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pagos (date, mes, professional, time, data, updated_at)
                VALUES (%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (date, professional, time) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (date, mes, professional, time, json.dumps(pago)))
            conn.commit()

def update_pago(date: str, professional: str, time: str, updates: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM pagos WHERE date=%s AND professional=%s AND time=%s", (date, professional, time))
            row = cur.fetchone()
            if not row:
                return
            data = dict(row["data"])
            data.update(updates)
            cur.execute("UPDATE pagos SET data=%s, updated_at=NOW() WHERE date=%s AND professional=%s AND time=%s",
                       (json.dumps(data), date, professional, time))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# COMISIONES
# ══════════════════════════════════════════════════════════════════════════════

def get_comisiones() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='comisiones'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {"default": 20}

def save_comisiones(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('comisiones', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# CAJA CONFIG
# ══════════════════════════════════════════════════════════════════════════════

def get_caja_config() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='caja_config'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def save_caja_config(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('caja_config', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# GASTOS
# ══════════════════════════════════════════════════════════════════════════════

def get_gastos() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='gastos'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def save_gastos(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('gastos', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()

def get_gastos_config() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='gastos_config'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def save_gastos_config(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('gastos_config', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TASAS RRHH
# ══════════════════════════════════════════════════════════════════════════════

def get_tasas() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='tasas'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def save_tasas(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('tasas', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# TRABAJADORES
# ══════════════════════════════════════════════════════════════════════════════

def get_trabajadores() -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM config WHERE key='trabajadores'")
            row = cur.fetchone()
            return dict(row["data"]) if row else {}

def save_trabajadores(data: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO config (key, data, updated_at) VALUES ('trabajadores', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()
            """, (json.dumps(data),))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

def log_acceso(usuario: str, accion: str = "ver_ficha", rut_paciente: str = None,
               rut: str = None, ip: str = None, detalle: str = None, tipo: str = None) -> None:
    rut_final = rut_paciente or rut
    accion_final = accion if accion != "ver_ficha" else (f"ver_ficha_{tipo}" if tipo else "ver_ficha")
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_log (usuario, accion, rut_paciente, ip, detalle)
                VALUES (%s, %s, %s, %s, %s)
            """, (usuario, accion_final, rut_final, ip, detalle))
            conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# SUSCRIPCIONES
# ══════════════════════════════════════════════════════════════════════════════

PRECIOS_ROL = {
    "medico":     30000,
    "kine":       25000,
    "psicologo":  30000,
    "secretaria": 20000,
    "admin":      20000,
}

PRECIOS_EXTERNO = {
    "externo_base":     35000,
    "externo_completo": 50000,
}


def calcular_precio_centro(roles: dict, descuento_pct: int = 0) -> dict:
    detalle = {}
    precio_base = 0
    for rol, cantidad in roles.items():
        precio_rol = PRECIOS_ROL.get(rol, 0)
        subtotal   = precio_rol * cantidad
        detalle[rol] = {"cantidad": cantidad, "precio_unitario": precio_rol, "subtotal": subtotal}
        precio_base += subtotal
    descuento_monto = int(precio_base * descuento_pct / 100)
    precio_final    = precio_base - descuento_monto
    return {
        "precio_base": precio_base, "descuento_pct": descuento_pct,
        "descuento_monto": descuento_monto, "precio_final": precio_final, "detalle": detalle,
    }


def get_suscripcion(centro_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM suscripciones WHERE centro_id = %s", (centro_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_all_suscripciones() -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM suscripciones ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]


def save_suscripcion(data: Dict[str, Any]) -> None:
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO suscripciones (
                    centro_id, nombre_centro, plan, roles, precio_base,
                    descuento_pct, descuento_motivo, descuento_hasta, precio_final,
                    estado, fecha_inicio, fecha_vencimiento, flow_customer_id,
                    flow_subscription_id, email_contacto, metodo_pago, created_at, updated_at
                ) VALUES (
                    %(centro_id)s, %(nombre_centro)s, %(plan)s, %(roles)s, %(precio_base)s,
                    %(descuento_pct)s, %(descuento_motivo)s, %(descuento_hasta)s, %(precio_final)s,
                    %(estado)s, %(fecha_inicio)s, %(fecha_vencimiento)s, %(flow_customer_id)s,
                    %(flow_subscription_id)s, %(email_contacto)s, %(metodo_pago)s, %(now)s, %(now)s
                )
                ON CONFLICT (centro_id) DO UPDATE SET
                    nombre_centro=EXCLUDED.nombre_centro, plan=EXCLUDED.plan,
                    roles=EXCLUDED.roles, precio_base=EXCLUDED.precio_base,
                    descuento_pct=EXCLUDED.descuento_pct, descuento_motivo=EXCLUDED.descuento_motivo,
                    descuento_hasta=EXCLUDED.descuento_hasta, precio_final=EXCLUDED.precio_final,
                    estado=EXCLUDED.estado, fecha_inicio=EXCLUDED.fecha_inicio,
                    fecha_vencimiento=EXCLUDED.fecha_vencimiento,
                    flow_customer_id=EXCLUDED.flow_customer_id,
                    flow_subscription_id=EXCLUDED.flow_subscription_id,
                    email_contacto=EXCLUDED.email_contacto,
                    metodo_pago=EXCLUDED.metodo_pago, updated_at=EXCLUDED.updated_at
            """, {
                "centro_id": data["centro_id"], "nombre_centro": data.get("nombre_centro", ""),
                "plan": data.get("plan", "centro"), "roles": json.dumps(data.get("roles", {})),
                "precio_base": data.get("precio_base", 0), "descuento_pct": data.get("descuento_pct", 0),
                "descuento_motivo": data.get("descuento_motivo", ""),
                "descuento_hasta": data.get("descuento_hasta"),
                "precio_final": data.get("precio_final", 0), "estado": data.get("estado", "activo"),
                "fecha_inicio": data.get("fecha_inicio"), "fecha_vencimiento": data.get("fecha_vencimiento"),
                "flow_customer_id": data.get("flow_customer_id"),
                "flow_subscription_id": data.get("flow_subscription_id"),
                "email_contacto": data.get("email_contacto", ""),
                "metodo_pago": data.get("metodo_pago", "manual"), "now": now,
            })
            conn.commit()


def update_suscripcion(centro_id: str, updates: Dict[str, Any]) -> None:
    now = _utc_now()
    sets = ", ".join(f"{k}=%({k})s" for k in updates)
    sets += ", updated_at=%(now)s"
    params = {**updates, "centro_id": centro_id, "now": now}
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE suscripciones SET {sets} WHERE centro_id=%(centro_id)s", params)
            conn.commit()


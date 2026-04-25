"""
db/supabase_client.py
---------------------
Capa única de acceso a Supabase (PostgreSQL).
Reemplaza todas las operaciones de disco JSON para:
  - pacientes
  - eventos clínicos
  - usuarios
  - profesionales

Uso:
    from db.supabase_client import (
        get_paciente, create_paciente, update_paciente,
        get_eventos, create_evento,
        get_users, save_users,
        get_profesionales
    )
"""

from __future__ import annotations

import os
import json
import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# ── Conexión ───────────────────────────────────────────────────────────────────

def _get_conn():
    url = os.environ.get("SUPABASE_DATABASE_URL")
    if not url:
        raise RuntimeError("Falta variable de entorno SUPABASE_DATABASE_URL")
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ══════════════════════════════════════════════════════════════════════════════
# PACIENTES
# ══════════════════════════════════════════════════════════════════════════════

def get_paciente(rut: str) -> Optional[Dict[str, Any]]:
    """Retorna la ficha administrativa de un paciente o None si no existe."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pacientes WHERE rut = %s", (rut,))
            row = cur.fetchone()
            return dict(row) if row else None


def create_paciente(data: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva ficha administrativa. Lanza error si ya existe."""
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
                "rut":               data["rut"],
                "nombre":            data.get("nombre", ""),
                "apellido_paterno":  data.get("apellido_paterno", ""),
                "apellido_materno":  data.get("apellido_materno", ""),
                "fecha_nacimiento":  data.get("fecha_nacimiento", ""),
                "sexo":              data.get("sexo", ""),
                "email":             data.get("email", ""),
                "telefono":          data.get("telefono", ""),
                "direccion":         data.get("direccion", ""),
                "ciudad":            data.get("ciudad", ""),
                "prevision":         data.get("prevision", ""),
                "ocupacion":         data.get("ocupacion", ""),
                "extra":             json.dumps(data.get("extra", {})),
                "created_at":        now,
                "updated_at":        now,
            })
            conn.commit()
            return dict(cur.fetchone())


def update_paciente(rut: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza una ficha administrativa existente."""
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE pacientes SET
                    nombre           = %(nombre)s,
                    apellido_paterno = %(apellido_paterno)s,
                    apellido_materno = %(apellido_materno)s,
                    fecha_nacimiento = %(fecha_nacimiento)s,
                    sexo             = %(sexo)s,
                    email            = %(email)s,
                    telefono         = %(telefono)s,
                    direccion        = %(direccion)s,
                    ciudad           = %(ciudad)s,
                    prevision        = %(prevision)s,
                    ocupacion        = %(ocupacion)s,
                    extra            = %(extra)s,
                    updated_at       = %(updated_at)s
                WHERE rut = %(rut)s
                RETURNING *
            """, {
                "rut":               rut,
                "nombre":            data.get("nombre", ""),
                "apellido_paterno":  data.get("apellido_paterno", ""),
                "apellido_materno":  data.get("apellido_materno", ""),
                "fecha_nacimiento":  data.get("fecha_nacimiento", ""),
                "sexo":              data.get("sexo", ""),
                "email":             data.get("email", ""),
                "telefono":          data.get("telefono", ""),
                "direccion":         data.get("direccion", ""),
                "ciudad":            data.get("ciudad", ""),
                "prevision":         data.get("prevision", ""),
                "ocupacion":         data.get("ocupacion", ""),
                "extra":             json.dumps(data.get("extra", {})),
                "updated_at":        now,
            })
            conn.commit()
            return dict(cur.fetchone())


def search_pacientes(q: str) -> List[Dict[str, Any]]:
    """Busca pacientes por RUT, nombre o apellido."""
    q_lower = f"%{q.lower()}%"
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM pacientes
                WHERE LOWER(rut)              LIKE %(q)s
                   OR LOWER(nombre)           LIKE %(q)s
                   OR LOWER(apellido_paterno) LIKE %(q)s
                   OR LOWER(apellido_materno) LIKE %(q)s
                ORDER BY apellido_paterno, nombre
                LIMIT 50
            """, {"q": q_lower})
            return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════════════════════════════════════════
# EVENTOS CLÍNICOS
# ══════════════════════════════════════════════════════════════════════════════

def get_eventos(rut: str) -> List[Dict[str, Any]]:
    """Retorna todos los eventos clínicos de un paciente, ordenados desc."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM eventos
                WHERE rut_paciente = %s
                ORDER BY fecha_hora DESC
            """, (rut,))
            rows = cur.fetchall()
            result = []
            for row in rows:
                ev = dict(row["contenido"])  # contenido es JSONB
                ev["_id"] = row["id"]
                ev["created_at"] = str(row["created_at"])
                result.append(ev)
            return result


def get_eventos_resumen(rut: str) -> List[Dict[str, Any]]:
    """Retorna resumen de eventos (fecha, hora, diagnóstico, profesional)."""
    eventos = get_eventos(rut)
    resumen = []
    for ev in eventos:
        professional_name = (
            ev.get("professional_name") or
            ev.get("professional_user") or
            ev.get("professional_id") or ""
        )
        resumen.append({
            "fecha":             ev.get("fecha"),
            "hora":              ev.get("hora"),
            "diagnostico":       ev.get("diagnostico"),
            "professional_name": professional_name,
            "created_at":        ev.get("created_at"),
        })
    return resumen


def create_evento(rut: str, evento: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda un nuevo evento clínico."""
    fecha_hora = f"{evento.get('fecha', '')}_{evento.get('hora', '').replace(':', '-')}"
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Verificar duplicado
            cur.execute("""
                SELECT id FROM eventos
                WHERE rut_paciente = %s AND fecha_hora = %s
            """, (rut, fecha_hora))
            if cur.fetchone():
                raise ValueError("Ya existe una atención en esa fecha y hora")

            cur.execute("""
                INSERT INTO eventos (
                    rut_paciente, professional_id, fecha_hora,
                    tipo, contenido, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                rut,
                evento.get("professional_id"),
                fecha_hora,
                evento.get("tipo", "consulta"),
                json.dumps(evento),
                now,
                now,
            ))
            conn.commit()
            row = cur.fetchone()
            evento["_id"] = row["id"]
            return evento


# ══════════════════════════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════════════════════════

def get_users() -> Dict[str, Any]:
    """Retorna todos los usuarios como dict {id: datos}."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios")
            rows = cur.fetchall()
            return {
                row["id"]: {
                    "password":     row["password"],
                    "active":       row["active"],
                    "professional": row["professional"],
                    "role":         row["role"],
                }
                for row in rows
            }


def save_user(user_id: str, data: Dict[str, Any]) -> None:
    """Crea o actualiza un usuario."""
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (id, password, active, professional, role, created_at, updated_at)
                VALUES (%(id)s, %(password)s, %(active)s, %(professional)s, %(role)s, %(now)s, %(now)s)
                ON CONFLICT (id) DO UPDATE SET
                    password     = EXCLUDED.password,
                    active       = EXCLUDED.active,
                    professional = EXCLUDED.professional,
                    role         = EXCLUDED.role,
                    updated_at   = EXCLUDED.updated_at
            """, {
                "id":           user_id,
                "password":     data.get("password", ""),
                "active":       data.get("active", True),
                "professional": data.get("professional"),
                "role":         json.dumps(data.get("role", {})),
                "now":          now,
            })
            conn.commit()


def save_users(users: Dict[str, Any]) -> None:
    """Guarda un dict completo de usuarios (compatibilidad con código existente)."""
    for user_id, data in users.items():
        save_user(user_id, data)


def load_users() -> Dict[str, Any]:
    """Alias de get_users() — compatibilidad con users_store existente."""
    return get_users()


# ══════════════════════════════════════════════════════════════════════════════
# PROFESIONALES
# ══════════════════════════════════════════════════════════════════════════════

def get_profesionales() -> Dict[str, Any]:
    """Retorna todos los profesionales activos con schedule."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM profesionales
                WHERE active = TRUE AND schedule IS NOT NULL
            """)
            rows = cur.fetchall()
            return {
                row["id"]: {
                    "id":           row["id"],
                    "name":         row["name"],
                    "rut":          row["rut"],
                    "specialty":    row["specialty"],
                    "active":       row["active"],
                    "schedule":     row["schedule"],
                    "blocked_dates": row["blocked_dates"] or [],
                }
                for row in rows
            }


def save_profesional(prof_id: str, data: Dict[str, Any]) -> None:
    """Crea o actualiza un profesional."""
    now = _utc_now()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO profesionales (
                    id, name, rut, specialty, active,
                    schedule, blocked_dates, created_at, updated_at
                ) VALUES (
                    %(id)s, %(name)s, %(rut)s, %(specialty)s, %(active)s,
                    %(schedule)s, %(blocked_dates)s, %(now)s, %(now)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    name          = EXCLUDED.name,
                    rut           = EXCLUDED.rut,
                    specialty     = EXCLUDED.specialty,
                    active        = EXCLUDED.active,
                    schedule      = EXCLUDED.schedule,
                    blocked_dates = EXCLUDED.blocked_dates,
                    updated_at    = EXCLUDED.updated_at
            """, {
                "id":           prof_id,
                "name":         data.get("name", ""),
                "rut":          data.get("rut", ""),
                "specialty":    data.get("specialty", ""),
                "active":       data.get("active", True),
                "schedule":     json.dumps(data.get("schedule", {})),
                "blocked_dates": data.get("blocked_dates", []),
                "now":          now,
            })
            conn.commit()


def init_db():
    """
    Crea todas las tablas si no existen.
    Llamar al arrancar el backend en main.py
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id           TEXT PRIMARY KEY,
                    password     TEXT NOT NULL,
                    active       BOOLEAN DEFAULT TRUE,
                    professional TEXT,
                    role         JSONB,
                    created_at   TIMESTAMPTZ DEFAULT NOW(),
                    updated_at   TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS profesionales (
                    id            TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    rut           TEXT,
                    specialty     TEXT,
                    active        BOOLEAN DEFAULT TRUE,
                    schedule      JSONB,
                    blocked_dates TEXT[],
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    updated_at    TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS pacientes (
                    rut              TEXT PRIMARY KEY,
                    nombre           TEXT,
                    apellido_paterno TEXT,
                    apellido_materno TEXT,
                    fecha_nacimiento TEXT,
                    sexo             TEXT,
                    email            TEXT,
                    telefono         TEXT,
                    direccion        TEXT,
                    ciudad           TEXT,
                    prevision        TEXT,
                    ocupacion        TEXT,
                    extra            JSONB,
                    created_at       TIMESTAMPTZ DEFAULT NOW(),
                    updated_at       TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS eventos (
                    id              SERIAL PRIMARY KEY,
                    rut_paciente    TEXT NOT NULL REFERENCES pacientes(rut),
                    professional_id TEXT REFERENCES profesionales(id),
                    fecha_hora      TEXT NOT NULL,
                    tipo            TEXT,
                    contenido       JSONB NOT NULL,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_eventos_rut   ON eventos(rut_paciente);
                CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha_hora);

                CREATE TABLE IF NOT EXISTS sedes (
                    id         TEXT PRIMARY KEY,
                    regiones   JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS trabajadores (
                    id         SERIAL PRIMARY KEY,
                    data       JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS gastos (
                    id         SERIAL PRIMARY KEY,
                    periodo    TEXT NOT NULL,
                    data       JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS comisiones (
                    id         SERIAL PRIMARY KEY,
                    data       JSONB NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            conn.commit()
            print("✅ [DB] Tablas verificadas/creadas correctamente")

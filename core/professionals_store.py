"""
core/professionals_store.py
---------------------------
Reemplaza lectura/escritura de /data/professionals.json → Supabase
Mantiene la misma interfaz para compatibilidad.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from db.supabase_client import _get_conn, _utc_now, get_profesionales, save_profesional
from db.supabase_client import get_users, save_user


def _es_interno(p: Dict[str, Any]) -> bool:
    id_str   = str(p.get("id", "")).lower().replace(" ", "_")
    name_str = str(p.get("name", "")).lower()
    return (
        id_str.startswith("ia_") or
        "prediagnóstico" in name_str or
        "prediagnostico" in name_str
    )


def list_professionals(only_public: bool = False) -> List[Dict[str, Any]]:
    profs = list(get_profesionales().values())
    if only_public:
        return [p for p in profs if not _es_interno(p)]
    return profs


def get_professional(pid: str) -> Optional[Dict[str, Any]]:
    return get_profesionales().get(pid)


def add_professional(professional: Dict[str, Any]) -> Dict[str, Any]:
    pid = professional.get("id")
    if not pid:
        raise ValueError("Falta campo obligatorio: id")

    if get_professional(pid):
        raise ValueError("Profesional ya existe")

    save_profesional(pid, professional)

    users    = get_users()
    username = professional.get("username") or pid

    if username not in users:
        role = professional.get("role", "medico")
        save_user(username, {
            "password":     professional.get("password", "cambiar123"),
            "role": {
                "name":  role,
                "entry": f"/{role}",
                "allow": ["agenda", "pacientes", "atencion", "documentos"]
            },
            "professional": pid,
            "active":       True
        })

    return professional


def update_professional(pid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    prof = get_professional(pid)
    if not prof:
        raise ValueError("Profesional no existe")
    prof.update(updates)
    save_profesional(pid, prof)
    return prof


def delete_professional(pid: str) -> Dict[str, Any]:
    # Buscar por id O por cualquier campo relacionado — sin filtro de active
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM profesionales 
                WHERE id = %s
                   OR id IN (SELECT professional FROM usuarios WHERE id = %s)
            """, (pid, pid))
            row = cur.fetchone()

    if not row:
        # Último intento — borrar directo aunque no exista el registro
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM profesionales WHERE id = %s", (pid,))
                cur.execute("DELETE FROM usuarios WHERE id = %s", (pid,))
                cur.execute("DELETE FROM sedes WHERE id = %s", (pid,))
                conn.commit()
        return {"id": pid, "deleted": True}

    prof     = dict(row)
    real_pid = prof["id"]
    username = pid  # el username es el pid que vino del frontend

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM profesionales WHERE id = %s", (real_pid,))
            cur.execute("DELETE FROM usuarios WHERE id = %s OR professional = %s", (username, real_pid))
            cur.execute("DELETE FROM sedes WHERE id = %s OR id = %s", (real_pid, username))
            conn.commit()

    return prof
    

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

ENTRY_MAP = {
    "medico":     "/medico",
    "kine":       "/kine",
    "psicologo":  "/psicologo",
    "secretaria": "/secretaria",
    "admin":      "/admin",
}

ALLOW_MAP = {
    "medico":     ["agenda", "pacientes", "atencion", "documentos"],
    "kine":       ["agenda", "pacientes"],
    "psicologo":  ["agenda", "pacientes"],
    "secretaria": ["agenda", "pacientes"],
    "admin":      ["agenda", "pacientes", "atencion", "documentos", "administracion"],
}


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


def _get_professional_any(pid: str) -> Optional[Dict[str, Any]]:
    """Busca profesional incluyendo inactivos — para operaciones de delete."""
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM profesionales WHERE id = %s", (pid,))
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception:
        return None


def add_professional(professional: Dict[str, Any]) -> Dict[str, Any]:
    pid = professional.get("id")
    if not pid:
        raise ValueError("Falta campo obligatorio: id")

    if get_professional(pid):
        raise ValueError("Profesional ya existe")

    save_profesional(pid, professional)

    # Crear usuario automáticamente
    users    = get_users()
    username = professional.get("username") or pid

    if username not in users:
        rol_raw = professional.get("role", "medico")
        rol     = rol_raw if isinstance(rol_raw, str) else rol_raw.get("name", "medico")
        scope   = professional.get("scope", "ica")

        save_user(username, {
            "password":     professional.get("password", "cambiar123"),
            "role": {
                "name":  rol,
                "entry": ENTRY_MAP.get(rol, f"/{rol}"),
                "allow": ALLOW_MAP.get(rol, ["agenda", "pacientes"]),
                "scope": scope,
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
    # Buscar incluyendo inactivos
    prof = _get_professional_any(pid)
    if not prof:
        raise ValueError("Profesional no existe")

    username = prof.get("username") or pid

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM profesionales WHERE id = %s", (pid,))
            cur.execute("DELETE FROM usuarios WHERE id = %s OR id = %s", (username, pid))
            cur.execute("DELETE FROM sedes WHERE id = %s", (pid,))
            conn.commit()

    return prof
    

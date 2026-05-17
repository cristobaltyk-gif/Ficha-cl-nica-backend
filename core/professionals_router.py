from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from core.professionals_store import (
    list_professionals,
    add_professional,
    update_professional,
    delete_professional,
)
from db.supabase_client import _get_conn, get_users

router = APIRouter(prefix="/professionals", tags=["professionals"])


def _get_scope(request: Request) -> Optional[str]:
    username = request.headers.get("X-Internal-User")
    if not username:
        return None
    u = get_users().get(username, {})
    return (u.get("role") or {}).get("scope")


def _load_sedes() -> dict:
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, regiones FROM sedes")
                rows = cur.fetchall()
                return {row["id"]: {"regiones": row["regiones"]} for row in rows}
    except Exception:
        return {}


def _filtrar_por_region(professionals: list, region: str) -> list:
    sedes = _load_sedes()
    if not sedes:
        return professionals
    resultado = []
    for p in professionals:
        pid       = p.get("id") or ""
        sede_prof = sedes.get(pid) or {}
        regiones  = sede_prof.get("regiones") or {}
        if region in regiones:
            resultado.append(p)
    return resultado if resultado else professionals


@router.get("")
def get_all(request: Request, public: bool = False, region: Optional[str] = None, scope: Optional[str] = None):
    profs = list_professionals(only_public=public)

    if public and scope:
        users = get_users()
        profs = [
            p for p in profs
            if (users.get(p.get("id"), {}).get("role") or {}).get("scope", "ica") == scope
        ]
    else:
        internal_scope = _get_scope(request)
        if internal_scope:
            users = get_users()
            profs = [
                p for p in profs
                if (users.get(p.get("id"), {}).get("role") or {}).get("scope", "ica") == internal_scope
            ]

    if region:
        profs = _filtrar_por_region(profs, region)
    return profs


@router.post("")
def create(professional: dict):
    try:
        result = add_professional(professional)

        email    = professional.get("email")
        username = professional.get("username") or professional.get("id")
        password = professional.get("password", "cambiar123")
        role     = professional.get("role", "medico")

        if email and username:
            try:
                from notifications.email_suscripciones import enviar_credenciales_externo
                enviar_credenciales_externo(
                    email_contacto=email,
                    nombre=professional.get("name", username),
                    username=username,
                    password_temp=password,
                    plan=role,
                )
                print(f"[PROFESSIONALS] ✅ Credenciales enviadas a {email}")
            except Exception as e:
                print(f"[PROFESSIONALS] ⚠️ Error enviando credenciales: {e}")

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{pid}")
def update(pid: str, updates: dict):
    try:
        return update_professional(pid, updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{pid}")
def remove(pid: str):
    try:
        return delete_professional(pid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
def get_all(request: Request, public: bool = False, region: Optional[str] = None):
    profs = list_professionals(only_public=public)

    scope = _get_scope(request)
    if scope:
        users = get_users()
        result = []
        for p in profs:
            pid        = p.get("id") or ""
            u          = users.get(pid, {})
            prof_scope = (u.get("role") or {}).get("scope") or "ica"
            if prof_scope == scope:
                result.append(p)
        profs = result

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

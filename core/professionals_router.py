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
    """Lee el scope del usuario autenticado desde X-Internal-User."""
    username = request.headers.get("X-Internal-User")
    if not username:
        return None
    users = get_users()
    u = users.get(username, {})
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

    # Filtrar por scope del admin autenticado
    scope = _get_scope(request)
    if scope and scope not in ("externo",):
        profs = [p for p in profs if (p.get("role") or {}).get("scope") == scope
                 or (p.get("role") is None)]

    if region:
        profs = _filtrar_por_region(profs, region)
    return profs


@router.post("")
def create(professional: dict):
    try:
        return add_professional(professional)
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

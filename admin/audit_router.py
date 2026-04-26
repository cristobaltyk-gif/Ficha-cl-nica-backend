"""
admin/audit_router.py
---------------------
Endpoints para consultar el log de accesos a fichas clínicas.
Cumplimiento Ley 21.668.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from auth.internal_auth import require_internal_auth
from db.supabase_client import _get_conn

router = APIRouter(prefix="/admin/audit", tags=["Audit Log"])


def _require_admin(user: dict):
    if user.get("role", {}).get("name") != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo administradores")


@router.get("")
def get_audit_log(
    rut: Optional[str] = Query(None),
    usuario: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    user=Depends(require_internal_auth)
):
    """Consulta el log de accesos. Filtrable por RUT o usuario."""
    _require_admin(user)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if rut:
                cur.execute("""
                    SELECT * FROM audit_log WHERE rut_paciente = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (rut, limit))
            elif usuario:
                cur.execute("""
                    SELECT * FROM audit_log WHERE usuario = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (usuario, limit))
            else:
                cur.execute("""
                    SELECT * FROM audit_log
                    ORDER BY created_at DESC LIMIT %s
                """, (limit,))
            rows = cur.fetchall()
    return {
        "total": len(rows),
        "registros": [dict(r) for r in rows]
    }
  

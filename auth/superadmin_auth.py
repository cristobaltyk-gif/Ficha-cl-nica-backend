"""
auth/superadmin_auth.py
Autenticación por API key para el superadministrador de la plataforma.
La clave vive en la variable de entorno SUPERADMIN_API_KEY — nunca en BD.
"""
from __future__ import annotations

import os
from fastapi import Header, HTTPException


def require_superadmin(x_superadmin_key: str = Header(None)) -> str:
    """
    Valida el header X-Superadmin-Key contra la variable de entorno.
    Usar como: Depends(require_superadmin)
    """
    key = os.getenv("SUPERADMIN_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Superadmin no configurado — falta SUPERADMIN_API_KEY"
        )
    if not x_superadmin_key or x_superadmin_key != key:
        raise HTTPException(
            status_code=403,
            detail="No autorizado"
        )
    return x_superadmin_key
  

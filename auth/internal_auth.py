from fastapi import Header, HTTPException
from auth.users_store import USERS

def require_internal_auth(x_internal_user: str = Header(None)):
    """
    Auth INTERNO para endpoints privados.
    NO usa login.
    NO usa sesión.
    NO usa JWT.

    Se valida contra USERS (fuente de verdad).
    """

    if not x_internal_user:
        raise HTTPException(
            status_code=401,
            detail="Falta header X-Internal-User"
        )

    user = USERS.get(x_internal_user)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario interno no existe"
        )

    if not user.get("active", False):
        raise HTTPException(
            status_code=401,
            detail="Usuario interno desactivado"
        )

    return {
        "usuario": x_internal_user,
        "role": user.get("role"),
        "professional": user.get("professional")
    }

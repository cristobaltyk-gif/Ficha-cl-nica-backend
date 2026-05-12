from fastapi import APIRouter, HTTPException, Request
from db.supabase_client import (
    _get_conn, get_users, save_user,
    get_centro, get_usuarios_centro
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _get_scope(request: Request):
    username = request.headers.get("X-Internal-User")
    if not username:
        return None
    u = get_users().get(username, {})
    return (u.get("role") or {}).get("scope")


@router.get("")
def list_users(request: Request):
    scope = _get_scope(request)
    users = get_users()
    result = []
    for username, u in users.items():
        if username == "public_web":
            continue
        user_scope = (u.get("role") or {}).get("scope")
        if scope and user_scope != scope:
            continue
        result.append({
            "username":     username,
            "role":         u.get("role"),
            "professional": u.get("professional"),
            "active":       u.get("active", True),
        })
    return result


@router.post("")
def create_user(data: dict):
    username = data.get("username")
    if not username:
        raise HTTPException(400, "Falta username")
    password = data.get("password")
    if not password:
        raise HTTPException(400, "Falta password")

    rol   = data.get("role", "secretaria")
    scope = data.get("scope", "ica")

    if scope not in ("ica", "externo"):
        raise HTTPException(400, "scope debe ser 'ica' o 'externo'")

    # Verificar capacidad del centro en backend
    if scope != "externo":
        try:
            centro = get_centro(scope)
            if centro:
                max_u  = centro.get("max_usuarios") or {}
                maximo = max_u.get(rol, 0)
                if maximo > 0:
                    usuarios = get_usuarios_centro(scope)
                    actual   = sum(1 for u in usuarios if (u.get("role") or {}).get("name") == rol)
                    if actual >= maximo:
                        raise HTTPException(403, f"Límite alcanzado para {rol}: {actual}/{maximo} usuarios")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[USERS] Error verificando capacidad: {e}")

    # Verificar si ya existe en PostgreSQL
    if username in get_users():
        raise HTTPException(409, "Usuario ya existe")

    entry_map = {
        "admin":      "/admin",
        "secretaria": "/secretaria",
        "medico":     "/medico",
        "kine":       "/kine",
        "psicologo":  "/psicologo",
    }
    allow_map = {
        "admin":      ["agenda", "pacientes", "atencion", "documentos", "administracion"],
        "secretaria": ["agenda", "pacientes"],
        "medico":     ["agenda", "pacientes", "atencion", "documentos"],
        "kine":       ["agenda", "pacientes"],
        "psicologo":  ["agenda", "pacientes"],
    }

    save_user(username, {
        "password":     password,
        "active":       data.get("active", True),
        "professional": data.get("professional", "system"),
        "role": {
            "name":  rol,
            "entry": entry_map.get(rol, f"/{rol}"),
            "allow": allow_map.get(rol, []),
            "scope": scope,
        }
    })
    return {"ok": True, "username": username}


@router.put("/{username}")
def update_user(username: str, data: dict):
    users = get_users()
    if username not in users:
        raise HTTPException(404, "Usuario no encontrado")

    u = users[username]
    if "password" in data and data["password"]:
        u["password"] = data["password"]
    if "active" in data:
        u["active"] = data["active"]
    if "role" in data:
        u["role"] = data["role"]
    if "scope" in data:
        if data["scope"] not in ("ica", "externo"):
            raise HTTPException(400, "scope debe ser 'ica' o 'externo'")
        if "role" not in data:
            u.setdefault("role", {})["scope"] = data["scope"]

    save_user(username, u)
    return {"ok": True}


@router.delete("/{username}")
def delete_user(username: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios     WHERE id = %s", (username,))
            cur.execute("DELETE FROM profesionales WHERE id = %s", (username,))
            cur.execute("DELETE FROM sedes         WHERE id = %s", (username,))
            conn.commit()

    return {"ok": True}

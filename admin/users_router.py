from fastapi import APIRouter, HTTPException
from auth.users_store import load_users, save_users

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


# ======================================================
# GET — lista todos los usuarios (sin passwords)
# ======================================================
@router.get("")
def list_users():
    users = load_users()
    result = []
    for username, u in users.items():
        result.append({
            "username":     username,
            "role":         u.get("role"),
            "professional": u.get("professional"),
            "active":       u.get("active", True),
        })
    return result


# ======================================================
# POST — crear usuario
# ======================================================
@router.post("")
def create_user(data: dict):
    username = data.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Falta username")

    password = data.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Falta password")

    rol = data.get("role", "secretaria")

    users = load_users()

    if username in users:
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    # Construir rol completo según nombre
    entry_map = {
        "admin":      "/admin",
        "secretaria": "/secretaria",
        "medico":     "/medico",
        "kine":       "/kine",
    }
    allow_map = {
        "admin":      ["agenda", "pacientes", "atencion", "documentos", "administracion"],
        "secretaria": ["agenda", "pacientes"],
        "medico":     ["agenda", "pacientes", "atencion", "documentos"],
        "kine":       ["agenda", "pacientes"],
    }

    users[username] = {
        "password":     password,
        "active":       data.get("active", True),
        "professional": data.get("professional", "system"),
        "role": {
            "name":  rol,
            "entry": entry_map.get(rol, f"/{rol}"),
            "allow": allow_map.get(rol, [])
        }
    }

    save_users(users)
    return {"ok": True, "username": username}


# ======================================================
# PUT — actualizar usuario (password, active, rol)
# ======================================================
@router.put("/{username}")
def update_user(username: str, data: dict):
    users = load_users()

    if username not in users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if "password" in data and data["password"]:
        users[username]["password"] = data["password"]

    if "active" in data:
        users[username]["active"] = data["active"]

    if "role" in data:
        users[username]["role"] = data["role"]

    save_users(users)
    return {"ok": True}


# ======================================================
# DELETE — eliminar usuario
# ======================================================
@router.delete("/{username}")
def delete_user(username: str):
    users = load_users()

    if username not in users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    del users[username]
    save_users(users)
    return {"ok": True}
  

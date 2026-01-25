from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse, RoleSchema
from auth.users_store import USERS

login_router = APIRouter()

# ===============================
# ROLES CANÓNICOS
# ===============================
ROLES = {
    "secretaria": {
        "name": "secretaria",
        "entry": "/secretaria",
        "allow": ["agenda", "pacientes"]
    },
    "medico": {
        "name": "medico",
        "entry": "/medico",
        "allow": ["agenda", "pacientes", "fichas"]
    },
    "admin": {
        "name": "admin",
        "entry": "/admin",
        "allow": ["agenda", "pacientes", "fichas", "usuarios"]
    }
}


# ===============================
# LOGIN
# ===============================
@login_router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):

    user = USERS.get(data.usuario)

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    if not user["active"]:
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    if user["password"] != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    # ✅ ROLE debe ser string
    role_name = user["role"]

    if isinstance(role_name, dict):
        role_name = role_name.get("name")

    if role_name not in ROLES:
        raise HTTPException(status_code=500, detail="Rol inválido")

    role_data = ROLES[role_name]

    return LoginResponse(
        usuario=data.usuario,
        role=RoleSchema(**role_data)
    )

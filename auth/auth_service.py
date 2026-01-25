from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse
from auth.users_store import USERS

login_router = APIRouter()

# ===============================
# DEFINICIÓN CANÓNICA DE ROLES
# ===============================
ROLES = {
    "secretaria": {
        "name": "secretaria",
        "entry": "/secretaria",
        "allow": ["agenda", "pacientes"]
    },
    "medico": {
        "name": "medico",
        "entry": "/agenda",
        "allow": ["agenda", "atencion", "documentos"]
    },
    "admin": {
        "name": "admin",
        "entry": "/administracion",
        "allow": ["agenda", "pacientes", "atencion", "documentos", "administracion"]
    }
}

@login_router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = USERS.get(data.usuario)

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    if not user["active"]:
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    if user["password"] != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    role_name = user["role"]

    if role_name not in ROLES:
        raise HTTPException(status_code=500, detail="Rol mal configurado en backend")

    return LoginResponse(
        usuario=data.usuario,
        role=ROLES[role_name]
    )

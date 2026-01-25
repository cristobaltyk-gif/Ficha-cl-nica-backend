from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse, RoleSchema
from auth.users_store import USERS

login_router = APIRouter()

# ===============================
# DEFINICIÓN CANÓNICA DE ROLES
# (OBJETO, NO STRING)
# ===============================
ROLES: dict[str, dict] = {
    "secretaria": {
        "name": "secretaria",
        "entry": "/secretaria",
        "allow": [
            "/agenda",
            "/pacientes"
        ]
    },
    "medico": {
        "name": "medico",
        "entry": "/agenda",
        "allow": [
            "/agenda",
            "/atencion",
            "/documentos"
        ]
    },
    "admin": {
        "name": "admin",
        "entry": "/administracion",
        "allow": [
            "/agenda",
            "/pacientes",
            "/atencion",
            "/documentos",
            "/administracion"
        ]
    }
}

# ===============================
# LOGIN
# ===============================
@login_router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):

    # 1️⃣ Usuario existe
    user = USERS.get(data.usuario)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    # 2️⃣ Usuario activo
    if not user.get("active", False):
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    # 3️⃣ Password correcta
    if user.get("password") != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    # 4️⃣ Rol válido
    role_name = user.get("role")
    if role_name not in ROLES:
        raise HTTPException(
            status_code=500,
            detail=f"Rol '{role_name}' mal configurado en backend"
        )

    role_data = ROLES[role_name]

    # 5️⃣ Respuesta FINAL (OBJETO)
    return LoginResponse(
        usuario=data.usuario,
        role=RoleSchema(**role_data)
    )

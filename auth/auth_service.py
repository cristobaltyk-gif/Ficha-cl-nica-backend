from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse, RoleSchema
from auth.users_store import USERS

login_router = APIRouter()

# ===============================
# LOGIN (BACKEND = FUENTE DE VERDAD)
# ===============================
@login_router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):

    # -------------------------------
    # Buscar usuario
    # -------------------------------
    user = USERS.get(data.usuario)

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    if not user.get("active", False):
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    if user.get("password") != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    # -------------------------------
    # Rol viene COMPLETO desde users.json
    # -------------------------------
    role_data = user.get("role")
    if not role_data:
        raise HTTPException(status_code=500, detail="Usuario sin rol definido")

    # -------------------------------
    # Professional SOLO si existe
    # (NO se inventa, NO se asume)
    # -------------------------------
    professional = user.get("professional")  # puede ser None

    # -------------------------------
    # Respuesta FINAL
    # -------------------------------
    return LoginResponse(
        usuario=data.usuario,
        role=RoleSchema(**role_data),
        professional=professional
    )

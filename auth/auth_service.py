from fastapi import APIRouter, HTTPException
from models.schemas import LoginRequest, LoginResponse
from auth.users_store import USERS

login_router = APIRouter()

@login_router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = USERS.get(data.usuario)

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    if not user["active"]:
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    if user["password"] != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    return LoginResponse(
        usuario=data.usuario,
        role=user["role"]
    )

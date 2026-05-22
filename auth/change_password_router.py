from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth.internal_auth import require_internal_auth
from db.supabase_client import get_users, save_user

router = APIRouter(prefix="/auth", tags=["Auth"])

class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nuevo:  str

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user=Depends(require_internal_auth)
):
    usuario = user["usuario"]
    users   = get_users()

    if usuario not in users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if users[usuario].get("password") != data.password_actual:
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if not data.password_nuevo or len(data.password_nuevo) < 6:
        raise HTTPException(status_code=400, detail="La contraseña nueva debe tener al menos 6 caracteres")

    users[usuario]["password"] = data.password_nuevo
    save_user(usuario, users[usuario])

    return {"ok": True}

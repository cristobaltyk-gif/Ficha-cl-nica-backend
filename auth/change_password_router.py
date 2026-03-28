from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth.internal_auth import require_internal_auth
from auth.users_store import USERS
import json
from pathlib import Path

router = APIRouter(prefix="/auth", tags=["Auth"])

DATA_FILE = Path("data/users.json")

class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nuevo:  str

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user=Depends(require_internal_auth)
):
    usuario = user["usuario"]

    if usuario not in USERS:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if USERS[usuario].get("password") != data.password_actual:
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    if not data.password_nuevo or len(data.password_nuevo) < 6:
        raise HTTPException(status_code=400, detail="La contraseña nueva debe tener al menos 6 caracteres")

    # Actualizar en memoria y en disco
    USERS[usuario]["password"] = data.password_nuevo

    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
        users_data[usuario]["password"] = data.password_nuevo
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    return {"ok": True}

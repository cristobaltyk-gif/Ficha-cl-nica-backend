from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware

# ===============================
# APP CENTRAL
# ===============================
app = FastAPI(
    title="Ficha Clínica - Backend Central",
    version="0.1"
)

# ===============================
# CORS (frontend)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego se restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# ROLES
# ===============================
ROLES = {
    "ADMIN",
    "MEDICO",
    "KINESIOLOGO",
    "SECRETARIA",
    "AUDITOR"
}

# ===============================
# USUARIOS (TEMPORAL - memoria)
# ===============================
USERS_DB: Dict[str, Dict] = {
    "admin": {
        "password": "admin123",
        "role": "ADMIN"
    },
    "medico1": {
        "password": "medico123",
        "role": "MEDICO"
    },
    "kine1": {
        "password": "kine123",
        "role": "KINESIOLOGO"
    },
    "secretaria1": {
        "password": "secre123",
        "role": "SECRETARIA"
    },
    "auditor1": {
        "password": "audit123",
        "role": "AUDITOR"
    }
}

# ===============================
# MODELOS
# ===============================
class LoginRequest(BaseModel):
    usuario: str
    clave: str


class LoginResponse(BaseModel):
    usuario: str
    role: str
    message: str


# ===============================
# ENDPOINT LOGIN
# ===============================
@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    user = USERS_DB.get(data.usuario)

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    if user["password"] != data.clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    return LoginResponse(
        usuario=data.usuario,
        role=user["role"],
        message="Login exitoso"
    )


# ===============================
# ENDPOINT CENTRAL (TEST)
# ===============================
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Ficha Clínica Backend Central",
        "roles": list(ROLES)
    }

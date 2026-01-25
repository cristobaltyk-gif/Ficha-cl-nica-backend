from pydantic import BaseModel
from typing import List

# ==========================
# REQUEST
# ==========================

class LoginRequest(BaseModel):
    usuario: str
    clave: str


# ==========================
# RESPONSE
# ==========================

class RoleSchema(BaseModel):
    name: str           # "SECRETARIA", "MEDICO", "ADMIN"
    entry: str          # "/secretaria", "/medico", etc.
    allow: List[str]    # ["agenda", "pacientes", ...]


class LoginResponse(BaseModel):
    usuario: str
    role: RoleSchema

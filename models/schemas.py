from pydantic import BaseModel
from typing import List, Optional

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
    name: str           # "secretaria", "medico", "kinesiologia", "nutricion", "admin"
    entry: str          # "/secretaria", "/medico", "/kine", "/nutricion", "/administracion"
    allow: List[str]    # ["agenda", "pacientes", "atencion", "documentos", ...]


class LoginResponse(BaseModel):
    usuario: str
    role: RoleSchema
    professional: Optional[str] = None
    # 👆 ID del profesional clínico (ej: "huerta", "kine_perez", "nutri_soto")
    # None para secretaria / admin

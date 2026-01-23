from pydantic import BaseModel

class LoginRequest(BaseModel):
    usuario: str
    clave: str

class LoginResponse(BaseModel):
    usuario: str
    role: str

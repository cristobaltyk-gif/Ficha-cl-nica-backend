from fastapi import APIRouter

router = APIRouter(prefix="/api/especialidades", tags=["Especialidades"])

ESPECIALIDADES_POR_ROL = {
    "medico": [
        "Cadera",
        "Rodilla",
        "Hombro",
        "Columna",
        "Tobillo",
        "Cirugía Articular",
        "Traumatología",
        "Dermatología",
        "Reumatología",
    ],
    "kine":      ["Kinesiología"],
    "psicologo": ["Psicología"],
}

@router.get("")
def get_especialidades():
    return ESPECIALIDADES_POR_ROL

@router.get("/{rol}")
def get_especialidades_rol(rol: str):
    return ESPECIALIDADES_POR_ROL.get(rol, [])

"""
modules/rrhh/router.py
Junta todos los sub-routers de RRHH en uno solo para incluir en main.py.
"""

from fastapi import APIRouter

from modules.rrhh.tasas        import router as tasas_router
from modules.rrhh.trabajadores import router as trabajadores_router
from modules.rrhh.liquidaciones import router as liquidaciones_router

router = APIRouter()
router.include_router(tasas_router)
router.include_router(trabajadores_router)
router.include_router(liquidaciones_router)

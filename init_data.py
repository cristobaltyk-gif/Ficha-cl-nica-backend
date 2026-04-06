"""
init_data.py — Inicialización de datos en disco persistente

Se ejecuta al arrancar FastAPI.
Si los archivos en /data/ no existen,
los copia desde data/ del repo (fuente de verdad inicial).
"""

import shutil
from pathlib import Path

# ============================================================
# FUENTES (repo)
# ============================================================
REPO_PROFESSIONALS = Path("data/professionals.json")
REPO_USERS         = Path("data/users.json")
REPO_REGIONES      = Path("data/regiones.geo.json")
REPO_SEDES         = Path("data/sedes.json")

# ============================================================
# DESTINOS (disco persistente Render)
# ============================================================
DISK_PROFESSIONALS = Path("/data/professionals.json")
DISK_USERS         = Path("/data/users.json")
DISK_REGIONES      = Path("/data/regiones.geo.json")
DISK_SEDES         = Path("/data/sedes.json")


def _init_file(repo: Path, disk: Path, fallback: str = "{}") -> None:
    if not disk.exists():
        if repo.exists():
            shutil.copy(repo, disk)
            print(f"✅ {disk} inicializado desde repo")
        else:
            disk.write_text(fallback, encoding="utf-8")
            print(f"⚠️  {disk} creado vacío (repo no encontrado)")
    else:
        print(f"ℹ️  {disk} ya existe")


def init_disk_data() -> None:
    Path("/data").mkdir(parents=True, exist_ok=True)

    _init_file(REPO_PROFESSIONALS, DISK_PROFESSIONALS)
    _init_file(REPO_USERS,         DISK_USERS)
    _init_file(REPO_REGIONES,      DISK_REGIONES, fallback='{"regiones":[]}')
    _init_file(REPO_SEDES,         DISK_SEDES,    fallback='{}')
    

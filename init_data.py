"""
init_data.py — Inicialización de datos en disco persistente

Se ejecuta al arrancar FastAPI.
Si /data/professionals.json o /data/users.json no existen,
los copia desde data/ del repo (fuente de verdad inicial).
"""

import shutil
from pathlib import Path

REPO_PROFESSIONALS = Path("data/professionals.json")
REPO_USERS         = Path("data/users.json")

DISK_PROFESSIONALS = Path("/data/professionals.json")
DISK_USERS         = Path("/data/users.json")


def init_disk_data() -> None:
    Path("/data").mkdir(parents=True, exist_ok=True)

    if not DISK_PROFESSIONALS.exists():
        if REPO_PROFESSIONALS.exists():
            shutil.copy(REPO_PROFESSIONALS, DISK_PROFESSIONALS)
            print("✅ /data/professionals.json inicializado desde repo")
        else:
            DISK_PROFESSIONALS.write_text("{}", encoding="utf-8")
    else:
        print("ℹ️  /data/professionals.json ya existe")

    if not DISK_USERS.exists():
        if REPO_USERS.exists():
            shutil.copy(REPO_USERS, DISK_USERS)
            print("✅ /data/users.json inicializado desde repo")
        else:
            DISK_USERS.write_text("{}", encoding="utf-8")
    else:
        print("ℹ️  /data/users.json ya existe")
        

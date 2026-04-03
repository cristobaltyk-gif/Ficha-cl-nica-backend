import json
from pathlib import Path
from threading import Lock
from typing import Dict, Any

DATA_FILE  = Path("/data/professionals.json")
USERS_FILE = Path("/data/users.json")
LOCK = Lock()


def _read_json() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text("{}", encoding="utf-8")
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(data: Dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_users(data: Dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _es_interno(p: Dict[str, Any]) -> bool:
    """Profesionales con id o username que empieza con ia_ son internos (ocultos al público)."""
    return (
        str(p.get("id", "")).startswith("ia_") or
        str(p.get("username", "")).startswith("ia_")
    )


def list_professionals(only_public: bool = False):
    profs = list(_read_json().values())
    if only_public:
        return [p for p in profs if not _es_interno(p)]
    return profs


def get_professional(pid: str):
    return _read_json().get(pid)


def add_professional(professional: Dict[str, Any]):
    """Crea profesional y su usuario automáticamente."""
    with LOCK:
        data = _read_json()

        pid = professional.get("id")
        if not pid:
            raise ValueError("Falta campo obligatorio: id")
        if pid in data:
            raise ValueError("Profesional ya existe")

        data[pid] = professional
        _write_json(data)

        # Crear usuario automáticamente
        users    = _read_users()
        username = professional.get("username") or pid

        if username not in users:
            role = professional.get("role", "medico")
            users[username] = {
                "password":     professional.get("password", "cambiar123"),
                "role": {
                    "name":  role,
                    "entry": f"/{role}",
                    "allow": ["agenda", "pacientes", "atencion", "documentos"]
                },
                "professional": pid,
                "active":       True
            }
            _write_users(users)

    return professional


def update_professional(pid: str, updates: Dict[str, Any]):
    with LOCK:
        data = _read_json()
        if pid not in data:
            raise ValueError("Profesional no existe")
        data[pid].update(updates)
        _write_json(data)
        return data[pid]


def delete_professional(pid: str):
    with LOCK:
        data = _read_json()
        if pid not in data:
            raise ValueError("Profesional no existe")
        removed = data.pop(pid)
        _write_json(data)
        return removed
        

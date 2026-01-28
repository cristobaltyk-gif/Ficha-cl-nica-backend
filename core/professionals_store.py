import json
from pathlib import Path
from typing import Dict, Any

DATA_FILE = Path("data/professionals.json")


# ======================================================
# HELPERS
# ======================================================

def _read_json() -> Dict[str, Any]:
    """
    Lee el archivo JSON completo.
    """
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(data: Dict[str, Any]) -> None:
    """
    Guarda el JSON completo en disco.
    """
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ======================================================
# LECTURA
# ======================================================

def list_professionals():
    """
    Devuelve lista completa (activos e inactivos).
    """
    data = _read_json()
    return list(data.values())


def get_professional(pid: str):
    """
    Devuelve un profesional por ID.
    """
    data = _read_json()
    return data.get(pid)


# ======================================================
# CREAR
# ======================================================

def add_professional(professional: Dict[str, Any]):
    """
    Agrega un profesional nuevo.
    ID obligatorio.
    """
    data = _read_json()

    pid = professional.get("id")
    if not pid:
        raise ValueError("Falta campo obligatorio: id")

    if pid in data:
        raise ValueError("Profesional ya existe")

    data[pid] = professional
    _write_json(data)

    return professional


# ======================================================
# UPDATE
# ======================================================

def update_professional(pid: str, updates: Dict[str, Any]):
    """
    Actualiza campos de un profesional existente.
    """
    data = _read_json()

    if pid not in data:
        raise ValueError("Profesional no existe")

    data[pid].update(updates)

    _write_json(data)
    return data[pid]


# ======================================================
# DELETE
# ======================================================

def delete_professional(pid: str):
    """
    Elimina un profesional del JSON.
    """
    data = _read_json()

    if pid not in data:
        raise ValueError("Profesional no existe")

    removed = data.pop(pid)

    _write_json(data)
    return removed

import json
from pathlib import Path

DATA_FILE = Path("data/professionals.json")


def load_professionals():
    """
    Lee profesionales desde JSON.
    """
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_active_professionals():
    """
    Devuelve solo profesionales activos.
    """
    professionals = load_professionals()

    return [
        p for p in professionals.values()
        if p.get("active")
    ]

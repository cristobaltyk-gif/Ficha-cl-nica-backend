import json
from pathlib import Path

DATA_FILE = Path("data/professionals.json")

def load_professionals():
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        professionals = json.load(f)

    # 🔒 Regla clínica: sin horario → no hay agenda
    valid = {}

    for pid, p in professionals.items():
        if not p.get("active"):
            continue

        if "schedule" not in p:
            # profesional mal configurado → se excluye
            continue

        valid[pid] = p

    return valid

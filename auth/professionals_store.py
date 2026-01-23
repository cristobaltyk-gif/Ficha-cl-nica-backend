import json
from pathlib import Path

DATA_FILE = Path("data/professionals.json")

def load_professionals():
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

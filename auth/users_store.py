import json
from pathlib import Path

DATA_FILE = Path("data/users.json")

def load_users():
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ ahora USERS viene del JSON
USERS = load_users()

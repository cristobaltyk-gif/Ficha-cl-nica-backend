# Documentospdf/professionalResolver.py

import os
import json


def getProfessionalData(professionalId: str):

    base_dir = os.path.dirname(__file__)
    professionals_path = os.path.join(base_dir, "professionals.json")

    try:
        with open(professionals_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get(professionalId)

    except Exception:
        return None

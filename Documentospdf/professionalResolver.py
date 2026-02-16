# Documentospdf/professionalResolver.py

import os
import json


def getProfessionalData(professionalId: str):

    # 📁 Documentospdf/
    base_dir = os.path.dirname(__file__)

    # 📁 ir a carpeta raíz del proyecto
    project_root = os.path.dirname(base_dir)

    # 📁 data/professionals.json
    professionals_path = os.path.join(
        project_root,
        "data",
        "professionals.json"
    )

    try:
        with open(professionals_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        medico = data.get(professionalId)

        if not medico:
            return None

        # 🔥 Firma y timbre automáticos según ID
        medico["firma"] = f"firma_{professionalId}.png"
        medico["timbre"] = f"timbre_{professionalId}.png"

        return medico

    except Exception as e:
        print("ERROR professionalResolver:", e)
        return None

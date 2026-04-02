"""
modules/rrhh/tasas.py
Tasas legales vigentes Chile — carga, guarda y endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from fastapi import APIRouter

router = APIRouter(prefix="/api/rrhh", tags=["RRHH - Tasas"])

TASAS_PATH = Path("/data/rrhh/tasas.json")
LOCK       = Lock()

DEFAULT_TASAS = {
    "afp": {
        "capital":   0.1130,
        "cuprum":    0.1144,
        "habitat":   0.1127,
        "modelo":    0.1058,
        "planvital": 0.1116,
        "provida":   0.1145,
        "uno":       0.1069,
    },
    "sis":                         0.0187,
    "salud_trabajador":            0.07,
    "afc_trabajador_indefinido":   0.006,
    "afc_trabajador_plazo_fijo":   0.011,
    "afc_empleador_indefinido":    0.0236,
    "afc_empleador_plazo_fijo":    0.03,
    "mutual":                      0.0093,
    "utm":                         66461,
    "tramos_impuesto": [
        {"desde": 0,        "hasta": 934234,    "tasa": 0.00,  "rebaja": 0},
        {"desde": 934234,   "hasta": 2075076,   "tasa": 0.04,  "rebaja": 37369},
        {"desde": 2075076,  "hasta": 3458460,   "tasa": 0.08,  "rebaja": 120373},
        {"desde": 3458460,  "hasta": 4841844,   "tasa": 0.135, "rebaja": 310594},
        {"desde": 4841844,  "hasta": 6225228,   "tasa": 0.23,  "rebaja": 770568},
        {"desde": 6225228,  "hasta": 8302972,   "tasa": 0.304, "rebaja": 1231505},
        {"desde": 8302972,  "hasta": 999999999, "tasa": 0.35,  "rebaja": 1613047},
    ]
}


def load_tasas() -> dict:
    if not TASAS_PATH.exists():
        TASAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASAS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TASAS, f, indent=2, ensure_ascii=False)
        return DEFAULT_TASAS
    with open(TASAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasas(data: dict) -> None:
    TASAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TASAS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.get("/tasas")
def get_tasas():
    return load_tasas()


@router.put("/tasas")
def update_tasas(data: dict):
    with LOCK:
        tasas = load_tasas()
        tasas.update(data)
        save_tasas(tasas)
    return {"ok": True}
  

"""
modules/contable/gastos_router.py
CRUD de gastos del centro médico.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/contable/gastos", tags=["Contable - Gastos"])

GASTOS_PATH = Path("/data/gastos.json")
CONFIG_PATH = Path("/data/gastos_config.json")
LOCK        = Lock()

# ======================================================
# CATEGORÍAS POR DEFECTO
# ======================================================

DEFAULT_CONFIG = {
    "grupos": {
        "fijos": {
            "label":       "Gastos Fijos",
            "categorias":  ["Arriendo", "Sueldos"]
        },
        "variables": {
            "label":       "Gastos Variables",
            "categorias":  ["Insumos médicos", "Equipamiento", "Marketing", "Otros"]
        },
        "cuentas": {
            "label":       "Cuentas",
            "categorias":  ["Servicios básicos", "Contabilidad", "Seguros"]
        }
    }
}


# ======================================================
# HELPERS
# ======================================================

def _load_gastos() -> dict:
    if not GASTOS_PATH.exists():
        return {}
    with open(GASTOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_gastos(data: dict) -> None:
    GASTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GASTOS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ======================================================
# SCHEMAS
# ======================================================

class GastoCreate(BaseModel):
    mes:        str        # YYYY-MM
    grupo:      str        # fijos | variables | cuentas
    categoria:  str
    descripcion: Optional[str] = ""
    monto:      int

class GastoUpdate(BaseModel):
    descripcion: Optional[str] = None
    monto:       Optional[int] = None

class CategoriaCreate(BaseModel):
    grupo:    str
    categoria: str


# ======================================================
# CONFIG — categorías
# ======================================================

@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config/categoria")
def add_categoria(data: CategoriaCreate):
    with LOCK:
        config = _load_config()
        grupo  = config["grupos"].get(data.grupo)
        if not grupo:
            raise HTTPException(status_code=404, detail="Grupo no existe")
        if data.categoria in grupo["categorias"]:
            raise HTTPException(status_code=409, detail="Categoría ya existe")
        grupo["categorias"].append(data.categoria)
        _save_config(config)
    return {"ok": True}


# ======================================================
# GASTOS — CRUD
# ======================================================

@router.get("/{mes}")
def get_gastos_mes(mes: str):
    gastos = _load_gastos()
    return gastos.get(mes, {})


@router.post("")
def create_gasto(data: GastoCreate):
    with LOCK:
        gastos = _load_gastos()
        mes    = gastos.setdefault(data.mes, {})
        grupo  = mes.setdefault(data.grupo, [])

        gasto_id = f"{data.mes}_{data.grupo}_{data.categoria}_{datetime.now().strftime('%H%M%S%f')}"

        grupo.append({
            "id":          gasto_id,
            "categoria":   data.categoria,
            "descripcion": data.descripcion or "",
            "monto":       data.monto,
            "created_at":  datetime.now().isoformat(timespec="seconds")
        })

        _save_gastos(gastos)
    return {"ok": True, "id": gasto_id}


@router.put("/{gasto_id}")
def update_gasto(gasto_id: str, data: GastoUpdate):
    with LOCK:
        gastos = _load_gastos()
        for mes_data in gastos.values():
            for grupo_list in mes_data.values():
                for gasto in grupo_list:
                    if gasto["id"] == gasto_id:
                        if data.descripcion is not None:
                            gasto["descripcion"] = data.descripcion
                        if data.monto is not None:
                            gasto["monto"] = data.monto
                        _save_gastos(gastos)
                        return {"ok": True}
    raise HTTPException(status_code=404, detail="Gasto no encontrado")


@router.delete("/{gasto_id}")
def delete_gasto(gasto_id: str):
    with LOCK:
        gastos = _load_gastos()
        for mes_data in gastos.values():
            for grupo_key, grupo_list in mes_data.items():
                for i, gasto in enumerate(grupo_list):
                    if gasto["id"] == gasto_id:
                        grupo_list.pop(i)
                        _save_gastos(gastos)
                        return {"ok": True}
    raise HTTPException(status_code=404, detail="Gasto no encontrado")
  

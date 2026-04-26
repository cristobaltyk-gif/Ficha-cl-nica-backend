"""
modules/contable/gastos_router.py
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.supabase_client import get_gastos, save_gastos, get_gastos_config, save_gastos_config

router = APIRouter(prefix="/api/contable/gastos", tags=["Contable - Gastos"])

DEFAULT_CONFIG = {
    "grupos": {
        "fijos":       {"label": "Gastos Fijos",      "categorias": ["Arriendo", "Sueldos"]},
        "variables":   {"label": "Gastos Variables",  "categorias": ["Insumos médicos", "Equipamiento", "Marketing", "Otros"]},
        "cuentas":     {"label": "Cuentas",            "categorias": ["Servicios básicos", "Contabilidad", "Seguros"]},
        "devoluciones":{"label": "Devoluciones",       "categorias": ["Devolución a paciente"]},
    }
}


def _load_config() -> dict:
    config = get_gastos_config()
    if not config:
        save_gastos_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    if "devoluciones" not in config.get("grupos", {}):
        config["grupos"]["devoluciones"] = DEFAULT_CONFIG["grupos"]["devoluciones"]
        save_gastos_config(config)
    return config


class GastoCreate(BaseModel):
    mes:         str
    grupo:       str
    categoria:   str
    descripcion: Optional[str] = ""
    monto:       int

class GastoUpdate(BaseModel):
    descripcion: Optional[str] = None
    monto:       Optional[int] = None

class CategoriaCreate(BaseModel):
    grupo:     str
    categoria: str


@router.get("/config")
def get_config():
    return _load_config()


@router.post("/config/categoria")
def add_categoria(data: CategoriaCreate):
    config = _load_config()
    grupo  = config["grupos"].get(data.grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no existe")
    if data.categoria in grupo["categorias"]:
        raise HTTPException(status_code=409, detail="Categoría ya existe")
    grupo["categorias"].append(data.categoria)
    save_gastos_config(config)
    return {"ok": True}


@router.get("/{mes}")
def get_gastos_mes(mes: str):
    return get_gastos().get(mes, {})


@router.post("")
def create_gasto(data: GastoCreate):
    gastos   = get_gastos()
    mes_data = gastos.setdefault(data.mes, {})
    grupo    = mes_data.setdefault(data.grupo, [])
    gasto_id = f"{data.mes}_{data.grupo}_{datetime.now().strftime('%H%M%S%f')}"
    grupo.append({
        "id":          gasto_id,
        "categoria":   data.categoria,
        "descripcion": data.descripcion or "",
        "monto":       data.monto,
        "created_at":  datetime.now().isoformat(timespec="seconds")
    })
    save_gastos(gastos)
    return {"ok": True, "id": gasto_id}


@router.put("/{gasto_id}")
def update_gasto(gasto_id: str, data: GastoUpdate):
    gastos = get_gastos()
    for mes_data in gastos.values():
        for grupo_list in mes_data.values():
            for gasto in grupo_list:
                if gasto["id"] == gasto_id:
                    if data.descripcion is not None:
                        gasto["descripcion"] = data.descripcion
                    if data.monto is not None:
                        gasto["monto"] = data.monto
                    save_gastos(gastos)
                    return {"ok": True}
    raise HTTPException(status_code=404, detail="Gasto no encontrado")


@router.delete("/{gasto_id}")
def delete_gasto(gasto_id: str):
    gastos = get_gastos()
    for mes_data in gastos.values():
        for grupo_key, grupo_list in mes_data.items():
            for i, gasto in enumerate(grupo_list):
                if gasto["id"] == gasto_id:
                    grupo_list.pop(i)
                    save_gastos(gastos)
                    return {"ok": True}
    raise HTTPException(status_code=404, detail="Gasto no encontrado")
    

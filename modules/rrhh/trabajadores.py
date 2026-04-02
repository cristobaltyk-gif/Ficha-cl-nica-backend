"""
modules/rrhh/trabajadores.py
CRUD trabajadores + lógica de cálculo de liquidación.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.rrhh.tasas import load_tasas

router = APIRouter(prefix="/api/rrhh", tags=["RRHH - Trabajadores"])

TRABAJADORES_PATH = Path("/data/rrhh/trabajadores.json")
LOCK              = Lock()

CARGOS = ["Secretaria", "Kinesiólogo", "Personal de aseo", "Guardia", "Recepcionista", "Otro"]


# ======================================================
# SCHEMAS
# ======================================================

class Bono(BaseModel):
    nombre: str
    monto:  int

class TrabajadorCreate(BaseModel):
    nombre:        str
    rut:           str
    cargo:         str
    tipo_contrato: str
    sueldo_base:   int
    afp:           str = "habitat"
    isapre:        bool = False
    monto_isapre:  int = 0
    activo:        bool = True
    bonos:         List[Bono] = [
        Bono(nombre="Bono colación",     monto=0),
        Bono(nombre="Bono movilización", monto=0),
    ]

class TrabajadorUpdate(BaseModel):
    nombre:        Optional[str]        = None
    cargo:         Optional[str]        = None
    tipo_contrato: Optional[str]        = None
    sueldo_base:   Optional[int]        = None
    afp:           Optional[str]        = None
    isapre:        Optional[bool]       = None
    monto_isapre:  Optional[int]        = None
    activo:        Optional[bool]       = None
    bonos:         Optional[List[Bono]] = None


# ======================================================
# HELPERS
# ======================================================

def load_trabajadores() -> dict:
    if not TRABAJADORES_PATH.exists():
        return {}
    with open(TRABAJADORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_trabajadores(data: dict) -> None:
    TRABAJADORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRABAJADORES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _clp(n: float) -> int:
    return int(round(n))


def _calcular_impuesto(base: int, tramos: list) -> int:
    for t in reversed(tramos):
        if base > t["desde"]:
            return max(_clp(base * t["tasa"] - t["rebaja"]), 0)
    return 0


# ======================================================
# CÁLCULO LIQUIDACIÓN
# ======================================================

def calcular_liquidacion(trabajador: dict, tasas: dict, mes: str) -> dict:
    tipo         = trabajador.get("tipo_contrato", "indefinido")
    sueldo_base  = trabajador.get("sueldo_base", 0)
    afp_nombre   = trabajador.get("afp", "habitat").lower()
    isapre       = trabajador.get("isapre", False)
    monto_isapre = trabajador.get("monto_isapre", 0)

    bonos       = trabajador.get("bonos", [
        {"nombre": "Bono colación",     "monto": 0},
        {"nombre": "Bono movilización", "monto": 0},
    ])
    total_bonos = sum(b.get("monto", 0) for b in bonos)

    if tipo == "honorarios":
        retencion = _clp(sueldo_base * 0.1075)
        return {
            "trabajador_id":    trabajador["id"],
            "nombre":           trabajador["nombre"],
            "rut":              trabajador.get("rut", ""),
            "cargo":            trabajador.get("cargo", ""),
            "tipo_contrato":    tipo,
            "mes":              mes,
            "sueldo_base":      sueldo_base,
            "bonos":            bonos,
            "total_bonos":      0,
            "retencion_boleta": retencion,
            "liquido":          sueldo_base - retencion,
            "costo_empresa":    sueldo_base,
            "es_honorarios":    True,
        }

    tasa_afp    = tasas["afp"].get(afp_nombre, 0.1127)
    desc_afp    = _clp(sueldo_base * tasa_afp)
    desc_salud  = _clp(sueldo_base * tasas["salud_trabajador"])
    if isapre and monto_isapre > desc_salud:
        desc_salud = monto_isapre

    afc_trab = (tasas["afc_trabajador_indefinido"] if tipo == "indefinido"
                else tasas["afc_trabajador_plazo_fijo"])
    desc_afc = _clp(sueldo_base * afc_trab)

    total_prevision  = desc_afp + desc_salud + desc_afc
    impuesto         = _calcular_impuesto(sueldo_base - total_prevision, tasas["tramos_impuesto"])
    total_descuentos = total_prevision + impuesto
    liquido          = sueldo_base - total_descuentos + total_bonos

    sis     = _clp(sueldo_base * tasas["sis"])
    mutual  = _clp(sueldo_base * tasas["mutual"])
    afc_emp = _clp(sueldo_base * (
        tasas["afc_empleador_indefinido"] if tipo == "indefinido"
        else tasas["afc_empleador_plazo_fijo"]
    ))

    return {
        "trabajador_id":       trabajador["id"],
        "nombre":              trabajador["nombre"],
        "rut":                 trabajador.get("rut", ""),
        "cargo":               trabajador.get("cargo", ""),
        "tipo_contrato":       tipo,
        "afp":                 afp_nombre.capitalize(),
        "salud":               "Isapre" if isapre else "Fonasa",
        "mes":                 mes,
        "sueldo_base":         sueldo_base,
        "bonos":               bonos,
        "total_bonos":         total_bonos,
        "descuento_afp":       desc_afp,
        "descuento_salud":     desc_salud,
        "descuento_afc":       desc_afc,
        "impuesto_unico":      impuesto,
        "total_descuentos":    total_descuentos,
        "liquido":             liquido,
        "costo_sis":           sis,
        "costo_mutual":        mutual,
        "costo_afc_empleador": afc_emp,
        "costo_empresa":       sueldo_base + total_bonos + sis + mutual + afc_emp,
        "es_honorarios":       False,
    }


# ======================================================
# ENDPOINTS
# ======================================================

@router.get("/trabajadores")
def list_trabajadores():
    return list(load_trabajadores().values())


@router.post("/trabajadores")
def create_trabajador(data: TrabajadorCreate):
    with LOCK:
        trabajadores = load_trabajadores()
        tid = data.rut.replace(".", "").replace("-", "")
        if tid in trabajadores:
            raise HTTPException(status_code=409, detail="Trabajador ya existe")
        trabajadores[tid] = {
            "id":            tid,
            "nombre":        data.nombre,
            "rut":           data.rut,
            "cargo":         data.cargo,
            "tipo_contrato": data.tipo_contrato,
            "sueldo_base":   data.sueldo_base,
            "afp":           data.afp,
            "isapre":        data.isapre,
            "monto_isapre":  data.monto_isapre,
            "activo":        data.activo,
            "bonos":         [b.dict() for b in data.bonos],
            "created_at":    datetime.now().isoformat(timespec="seconds"),
        }
        save_trabajadores(trabajadores)
    return trabajadores[tid]


@router.put("/trabajadores/{tid}")
def update_trabajador(tid: str, data: TrabajadorUpdate):
    with LOCK:
        trabajadores = load_trabajadores()
        if tid not in trabajadores:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")
        updates = data.dict(exclude_none=True)
        if "bonos" in updates:
            updates["bonos"] = [b if isinstance(b, dict) else b.dict() for b in updates["bonos"]]
        trabajadores[tid].update(updates)
        save_trabajadores(trabajadores)
        return trabajadores[tid]


@router.delete("/trabajadores/{tid}")
def delete_trabajador(tid: str):
    with LOCK:
        trabajadores = load_trabajadores()
        if tid not in trabajadores:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")
        del trabajadores[tid]
        save_trabajadores(trabajadores)
    return {"ok": True}
  

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/caja", tags=["Caja"])

CAJA_DIR    = Path("/data/caja")
PAGOS_DIR   = Path("/data/pagos")
AGENDA_PATH = Path("/data/agenda_future.json")
CONFIG_PATH = Path(os.path.dirname(__file__)) / "caja_config.json"

TIPOS_VALIDOS = {
    "particular", "control_costo", "control_gratuito",
    "sobrecupo", "cortesia", "kinesiologia"
}
TIPOS_GRATUITOS = {"control_gratuito", "cortesia"}
ESTADOS_VALIDOS = {"waiting", "paid"}
METODOS_VALIDOS = {"efectivo", "transferencia", "tarjeta"}

# =========================
# HELPERS
# =========================

def _month_key(date: str) -> str:
    return date[:7]  # "2026-03"

def _caja_path(date: str) -> Path:
    return CAJA_DIR / f"{_month_key(date)}.json"

def _pagos_path(date: str) -> Path:
    return PAGOS_DIR / f"{_month_key(date)}.json"

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_agenda_day(date: str, professional: str) -> dict:
    store = _load_json(AGENDA_PATH)
    return store.get("calendar", {}).get(date, {}).get(professional, {}).get("slots", {})

def _load_caja_slot(date: str, professional: str, time: str) -> dict:
    store = _load_json(_caja_path(date))
    return store.get(date, {}).get(professional, {}).get(time, {})

def _load_caja_day(date: str, professional: str) -> dict:
    store = _load_json(_caja_path(date))
    return store.get(date, {}).get(professional, {})

def _save_caja_slot(date: str, professional: str, time: str, slot: dict) -> None:
    path  = _caja_path(date)
    store = _load_json(path)
    store.setdefault(date, {}).setdefault(professional, {})[time] = slot
    _save_json(path, store)

def _load_pagos_day(date: str, professional: str) -> dict:
    store = _load_json(_pagos_path(date))
    return store.get(date, {}).get(professional, {})

def _save_pago(date: str, professional: str, time: str, pago: dict) -> None:
    path  = _pagos_path(date)
    store = _load_json(path)
    store.setdefault(date, {}).setdefault(professional, {})[time] = pago
    _save_json(path, store)

# =========================
# SCHEMAS
# =========================

class CajaUpdate(BaseModel):
    date:           str
    professional:   str
    time:           str
    arrival_status: Optional[str] = None
    tipo_atencion:  Optional[str] = None
    pagado:         Optional[bool] = None

class PagoCreate(BaseModel):
    date:             str
    professional:     str
    time:             str
    rut:              str
    tipo_atencion:    str
    metodo_pago:      Optional[str] = None
    numero_operacion: Optional[str] = None
    banco_origen:     Optional[str] = None
    pagado_por:       Optional[str] = None

class AnulacionCreate(BaseModel):
    date:         str
    professional: str
    time:         str
    motivo:       str
    anulado_por:  Optional[str] = None

# =========================
# GET — config
# =========================

@router.get("/config")
def get_config():
    return _load_config()

# =========================
# GET — panel del día
# =========================

@router.get("/day")
def get_caja_day(date: str, professional: str):
    agenda_slots = _load_agenda_day(date, professional)
    caja         = _load_caja_day(date, professional)
    config       = _load_config()

    result = []
    for time, slot in agenda_slots.items():
        if slot.get("status") not in ("reserved", "confirmed"):
            continue

        cs    = caja.get(time, {})
        tipo  = cs.get("tipo_atencion", "particular")
        monto = config.get(tipo, 0)

        result.append({
            "time":           time,
            "rut":            slot.get("rut", ""),
            "arrival_status": cs.get("arrival_status", "pending"),
            "tipo_atencion":  tipo,
            "monto":          monto,
            "pagado":         cs.get("pagado", False),
            "es_gratuito":    tipo in TIPOS_GRATUITOS,
        })

    result.sort(key=lambda x: x["time"])
    return {"date": date, "professional": professional, "slots": result}

# =========================
# PATCH — actualizar slot
# =========================

@router.patch("/slot")
def update_caja_slot(data: CajaUpdate):
    if data.arrival_status and data.arrival_status not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="arrival_status inválido")
    if data.tipo_atencion and data.tipo_atencion not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="tipo_atencion inválido")

    cs = _load_caja_slot(data.date, data.professional, data.time)

    if data.arrival_status is not None:
        cs["arrival_status"] = data.arrival_status
    if data.tipo_atencion is not None:
        config = _load_config()
        cs["tipo_atencion"] = data.tipo_atencion
        cs["monto"]         = config.get(data.tipo_atencion, 0)
        cs["es_gratuito"]   = data.tipo_atencion in TIPOS_GRATUITOS
    if data.pagado is not None:
        cs["pagado"] = data.pagado

    _save_caja_slot(data.date, data.professional, data.time, cs)
    return {"ok": True, "time": data.time}

# =========================
# POST — registrar pago
# =========================

@router.post("/pago")
def registrar_pago(data: PagoCreate):
    if data.tipo_atencion not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="tipo_atencion inválido")

    es_gratuito = data.tipo_atencion in TIPOS_GRATUITOS

    if not es_gratuito:
        if not data.metodo_pago or data.metodo_pago not in METODOS_VALIDOS:
            raise HTTPException(status_code=400, detail="metodo_pago inválido")
        if data.metodo_pago in ("transferencia", "tarjeta") and not data.numero_operacion:
            raise HTTPException(status_code=400, detail="numero_operacion requerido")

    config = _load_config()
    monto  = config.get(data.tipo_atencion, 0)

    _save_pago(data.date, data.professional, data.time, {
        "rut":              data.rut,
        "tipo_atencion":    data.tipo_atencion,
        "monto":            monto,
        "es_gratuito":      es_gratuito,
        "metodo_pago":      data.metodo_pago if not es_gratuito else None,
        "numero_operacion": data.numero_operacion,
        "banco_origen":     data.banco_origen,
        "pagado_at":        datetime.now().isoformat(timespec="seconds"),
        "pagado_por":       data.pagado_por,
        "anulado":          False,
        "anulacion_motivo": None,
        "anulacion_at":     None,
        "anulado_por":      None,
    })

    cs = _load_caja_slot(data.date, data.professional, data.time)
    cs["arrival_status"] = "paid"
    cs["pagado"]         = True
    cs["tipo_atencion"]  = data.tipo_atencion
    cs["monto"]          = monto
    _save_caja_slot(data.date, data.professional, data.time, cs)

    return {"ok": True, "monto": monto, "es_gratuito": es_gratuito}

# =========================
# POST — anular pago
# =========================

@router.post("/anular")
def anular_pago(data: AnulacionCreate):
    pagos = _load_pagos_day(data.date, data.professional)

    if data.time not in pagos:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pagos[data.time].get("anulado"):
        raise HTTPException(status_code=400, detail="Pago ya anulado")

    pagos[data.time]["anulado"]          = True
    pagos[data.time]["anulacion_motivo"] = data.motivo
    pagos[data.time]["anulacion_at"]     = datetime.now().isoformat(timespec="seconds")
    pagos[data.time]["anulado_por"]      = data.anulado_por

    path  = _pagos_path(data.date)
    store = _load_json(path)
    store.setdefault(data.date, {}).setdefault(data.professional, {})[data.time] = pagos[data.time]
    _save_json(path, store)

    cs = _load_caja_slot(data.date, data.professional, data.time)
    cs["arrival_status"] = None
    cs["pagado"]         = False
    _save_caja_slot(data.date, data.professional, data.time, cs)

    return {"ok": True}

# =========================
# GET — resumen del día
# =========================

@router.get("/summary")
def get_caja_summary(date: str, professional: str):
    day   = get_caja_day(date, professional)
    slots = day["slots"]
    pagos = _load_pagos_day(date, professional)

    total_pacientes = len(slots)
    esperando       = sum(1 for s in slots if s["arrival_status"] == "waiting" and not s["pagado"])
    pagados         = sum(1 for s in slots if s["pagado"])
    monto_total     = sum(p["monto"] for p in pagos.values() if not p.get("anulado", False))
    por_tipo        = {}
    por_metodo      = {}

    for p in pagos.values():
        if p.get("anulado"):
            continue
        t = p["tipo_atencion"]
        m = p.get("metodo_pago") or "gratuito"
        por_tipo[t]   = por_tipo.get(t, 0) + 1
        por_metodo[m] = por_metodo.get(m, 0) + 1

    return {
        "date":            date,
        "professional":    professional,
        "total_pacientes": total_pacientes,
        "esperando":       esperando,
        "pagados":         pagados,
        "monto_total":     monto_total,
        "por_tipo":        por_tipo,
        "por_metodo":      por_metodo,
    }
    

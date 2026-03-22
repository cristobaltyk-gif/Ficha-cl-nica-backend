from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os

router = APIRouter(prefix="/api/caja", tags=["Caja"])

CAJA_DIR    = "data/caja"
CONFIG_PATH = "caja_config.json"

TIPOS_VALIDOS   = {"particular", "control", "cortesia", "sobrecupo"}
ESTADOS_VALIDOS = {"waiting", "paid"}

# =========================
# HELPERS
# =========================

def _caja_path(date: str, professional: str) -> str:
    return os.path.join(CAJA_DIR, date, f"{professional}.json")

def _load_caja(date: str, professional: str) -> dict:
    path = _caja_path(date, professional)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_caja(date: str, professional: str, data: dict):
    path = _caja_path(date, professional)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_agenda(date: str, professional: str) -> dict:
    path = os.path.join("data/agenda", date, f"{professional}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# SCHEMAS
# =========================

class CajaUpdate(BaseModel):
    date:             str
    professional:     str
    time:             str
    arrival_status:   Optional[str] = None
    tipo_atencion:    Optional[str] = None
    pagado:           Optional[bool] = None

# =========================
# GET — panel del día
# =========================

@router.get("/day")
def get_caja_day(date: str, professional: str):
    agenda  = _load_agenda(date, professional)
    caja    = _load_caja(date, professional)
    config  = _load_config()

    result = []

    for time, slot in agenda.items():
        status = slot.get("status", "available")
        if status not in ("reserved", "confirmed"):
            continue

        caja_slot = caja.get(time, {})
        tipo      = caja_slot.get("tipo_atencion", "particular")
        monto     = config.get(tipo, 0)

        result.append({
            "time":           time,
            "rut":            slot.get("rut") or caja_slot.get("rut", ""),
            "patient":        slot.get("patient", {}),
            "arrival_status": caja_slot.get("arrival_status", "pending"),
            "tipo_atencion":  tipo,
            "monto":          monto,
            "pagado":         caja_slot.get("pagado", False),
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

    caja = _load_caja(data.date, data.professional)

    if data.time not in caja:
        caja[data.time] = {}

    if data.arrival_status is not None:
        caja[data.time]["arrival_status"] = data.arrival_status
    if data.tipo_atencion is not None:
        caja[data.time]["tipo_atencion"]  = data.tipo_atencion
        config = _load_config()
        caja[data.time]["monto"]          = config.get(data.tipo_atencion, 0)
    if data.pagado is not None:
        caja[data.time]["pagado"]         = data.pagado

    _save_caja(data.date, data.professional, caja)
    return {"ok": True, "time": data.time}

# =========================
# GET — resumen del día (totales)
# =========================

@router.get("/summary")
def get_caja_summary(date: str, professional: str):
    day    = get_caja_day(date, professional)
    slots  = day["slots"]

    total_pacientes = len(slots)
    esperando       = sum(1 for s in slots if s["arrival_status"] == "waiting")
    pagados         = sum(1 for s in slots if s["pagado"])
    monto_total     = sum(s["monto"] for s in slots if s["pagado"])
    por_tipo        = {}

    for s in slots:
        t = s["tipo_atencion"]
        por_tipo[t] = por_tipo.get(t, 0) + 1

    return {
        "date":             date,
        "professional":     professional,
        "total_pacientes":  total_pacientes,
        "esperando":        esperando,
        "pagados":          pagados,
        "monto_total":      monto_total,
        "por_tipo":         por_tipo,
    }

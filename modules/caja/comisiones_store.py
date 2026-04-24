# ============================================================
# comisiones_store.py
# Lee/escribe /data/comisiones.json
# Estructura: { "huerta": 30, "espinoza": 25, "default": 20 }
# ============================================================

import json
from pathlib import Path
from threading import Lock

COMISIONES_PATH = Path("/data/comisiones.json")
LOCK = Lock()

DEFAULT_PORCENTAJE = 20


def _read() -> dict:
    if not COMISIONES_PATH.exists():
        COMISIONES_PATH.parent.mkdir(parents=True, exist_ok=True)
        COMISIONES_PATH.write_text('{"default": 20}', encoding="utf-8")
        return {"default": DEFAULT_PORCENTAJE}
    with open(COMISIONES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    COMISIONES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COMISIONES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_all() -> dict:
    return _read()


def get_porcentaje(professional: str) -> int:
    data = _read()
    return data.get(professional, data.get("default", DEFAULT_PORCENTAJE))


def set_porcentaje(professional: str, porcentaje: int) -> dict:
    with LOCK:
        data = _read()
        data[professional] = porcentaje
        _write(data)
        return data


def delete_porcentaje(professional: str) -> dict:
    """Elimina override — vuelve a usar 'default'."""
    with LOCK:
        data = _read()
        if professional in data and professional != "default":
            del data[professional]
            _write(data)
        return data


def calcular(professional: str, monto: int) -> dict:
    """
    Dado un profesional y monto bruto, retorna:
    { bruto, porcentaje, retencion, neto }
    """
    porcentaje = get_porcentaje(professional)
    retencion  = round(monto * porcentaje / 100)
    return {
        "bruto":      monto,
        "porcentaje": porcentaje,
        "retencion":  retencion,
        "neto":       monto - retencion,
    }

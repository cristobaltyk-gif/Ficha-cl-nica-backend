"""
modules/caja/comisiones_store.py
"""
from db.supabase_client import get_comisiones, save_comisiones

DEFAULT_PORCENTAJE = 20


def get_all() -> dict:
    return get_comisiones()


def get_porcentaje(professional: str) -> int:
    data = get_comisiones()
    return data.get(professional, data.get("default", DEFAULT_PORCENTAJE))


def set_porcentaje(professional: str, porcentaje: int) -> dict:
    data = get_comisiones()
    data[professional] = porcentaje
    save_comisiones(data)
    return data


def delete_porcentaje(professional: str) -> dict:
    data = get_comisiones()
    if professional in data and professional != "default":
        del data[professional]
        save_comisiones(data)
    return data


def calcular(professional: str, monto: int) -> dict:
    porcentaje = get_porcentaje(professional)
    retencion  = round(monto * porcentaje / 100)
    return {
        "bruto":      monto,
        "porcentaje": porcentaje,
        "retencion":  retencion,
        "neto":       monto - retencion,
    }
    

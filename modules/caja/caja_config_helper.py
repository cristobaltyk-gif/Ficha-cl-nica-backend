"""
modules/caja/caja_config_helper.py
"""
from db.supabase_client import get_caja_config
from pathlib import Path
import json, os

_FALLBACK = Path(os.path.dirname(__file__)) / "caja_config.json"


def _load_config() -> dict:
    data = get_caja_config()
    if data:
        return data
    if _FALLBACK.exists():
        with open(_FALLBACK, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_tipos_profesional(professional_id: str) -> dict:
    config   = _load_config()
    por_prof = config.get("por_profesional", {})
    if professional_id in por_prof:
        return por_prof[professional_id]
    return {k: v for k, v in config.items() if k != "por_profesional"}


def get_valor_tipo(professional_id: str, tipo: str) -> int:
    config   = _load_config()
    por_prof = config.get("por_profesional", {})
    if professional_id in por_prof and tipo in por_prof[professional_id]:
        return por_prof[professional_id][tipo]
    return config.get(tipo, 0)
    

"""
modules/caja/caja_config_helper.py

Helpers para leer caja_config.json desde cualquier router.
Fuente única de verdad para valores de consulta.
"""

from pathlib import Path
import json
import os

CONFIG_PATH = Path(os.path.dirname(__file__)) / "caja_config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_tipos_profesional(professional_id: str) -> dict:
    """
    Devuelve los tipos y valores disponibles para un profesional.
    Si tiene config específica la usa, si no usa los valores globales.
    Excluye 'por_profesional' del resultado.
    """
    config = _load_config()
    por_prof = config.get("por_profesional", {})

    if professional_id in por_prof:
        return por_prof[professional_id]

    # Valores globales — excluir clave interna
    return {k: v for k, v in config.items() if k != "por_profesional"}


def get_valor_tipo(professional_id: str, tipo: str) -> int:
    """
    Devuelve el valor de un tipo de atención para un profesional.
    Fallback: valor global → 0.
    """
    config   = _load_config()
    por_prof = config.get("por_profesional", {})

    # Buscar en config específica del profesional
    if professional_id in por_prof:
        if tipo in por_prof[professional_id]:
            return por_prof[professional_id][tipo]

    # Fallback global
    return config.get(tipo, 0)

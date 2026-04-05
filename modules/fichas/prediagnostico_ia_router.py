# modules/fichas/prediagnostico_ia_router.py
# Recibe resultado del prediagnóstico y graba evento en ICA
# Llamado desde el backend de prediagnóstico tras emitir PDF
# Profesional grabador: ia_prediagnostico

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth

# ============================================================
# CONFIG
# ============================================================
BASE_DATA_PATH     = Path("/data/pacientes")
PROFESSIONALS_PATH = Path("/data/professionals.json")
IA_USER_KEY        = "ia_prediagnostico"
_LOCK              = Lock()

router = APIRouter(
    prefix="/api/prediagnostico",
    tags=["Prediagnóstico IA"],
)

# ============================================================
# SCHEMA
# ============================================================
class PrediagnosticoPayload(BaseModel):
    rut:           str
    nombre:        str
    edad:          Optional[int]  = None
    genero:        Optional[str]  = None
    dolor:         Optional[str]  = ""
    lado:          Optional[str]  = ""
    diagnostico:   Optional[str]  = ""
    examenes:      Optional[list] = []
    justificacion: Optional[str]  = ""
    idPago:        Optional[str]  = ""
    modulo:        Optional[str]  = "trauma"

# ============================================================
# HELPERS
# ============================================================
def _chile_now() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).isoformat()

def _get_professional_name(professional_id: str) -> str:
    try:
        if not PROFESSIONALS_PATH.exists():
            return professional_id
        data = json.loads(PROFESSIONALS_PATH.read_text(encoding="utf-8"))
        return data.get(professional_id, {}).get("name", professional_id)
    except Exception:
        return professional_id

# ============================================================
# NORMALIZAR EVENTO
# ============================================================
def _build_evento(
    payload: PrediagnosticoPayload,
    user: dict,
    professional_name: str,
) -> dict:
    now   = datetime.now(ZoneInfo("America/Santiago"))
    fecha = now.strftime("%Y-%m-%d")
    hora  = now.strftime("%H:%M")

    zona = payload.dolor or ""
    lado = payload.lado  or ""
    sint = f"{zona} {lado}".strip()

    examenes_txt = "\n".join(f"• {e}" for e in (payload.examenes or []) if e)

    atencion = (
        f"[PREDIAGNÓSTICO IA — pendiente validación médica]\n\n"
        f"Consulta iniciada vía sistema de prediagnóstico en línea.\n"
        f"Motivo: {sint or 'No especificado'}\n"
        f"Módulo: {payload.modulo or 'trauma'}\n"
        f"ID Pago: {payload.idPago or '—'}"
    )

    diagnostico = (
        f"[IA] {payload.diagnostico}\n\n"
        f"⚠️ Diagnóstico presuntivo generado por IA. "
        f"Debe ser validado por {professional_name}."
    ) if payload.diagnostico else "[IA] Sin diagnóstico presuntivo"

    examenes_campo = (
        f"Exámenes sugeridos por IA (pendiente validación médica):\n{examenes_txt}"
    ) if examenes_txt else ""

    indicaciones = (
        f"Justificación clínica IA:\n{payload.justificacion}"
    ) if payload.justificacion else ""

    return {
        "rut":                   payload.rut,
        "fecha":                 fecha,
        "hora":                  hora,
        "atencion":              atencion,
        "diagnostico":           diagnostico,
        "examenes":              examenes_campo,
        "indicaciones":          indicaciones,
        "receta":                "",
        "orden_kinesiologia":    "",
        "indicacion_quirurgica": "",
        "professional_id":       user["professional"],
        "professional_user":     user["usuario"],
        "professional_role":     user["role"],
        "professional_name":     professional_name,
        "created_at":            _chile_now(),
    }

# ============================================================
# ENDPOINT
# ============================================================
@router.post("/registrar")
def registrar_prediagnostico(
    payload: PrediagnosticoPayload,
    x_internal_user: str = Header(None),
):
    # 1. Auth — valida identidad y atribuciones
    user = require_internal_auth(x_internal_user=x_internal_user)

    # Solo ia_prediagnostico puede usar este endpoint
    if user["usuario"] != IA_USER_KEY:
        raise HTTPException(status_code=403, detail="Sin atribuciones para este endpoint")

    # 2. Nombre del profesional desde professionals.json
    professional_name = _get_professional_name(user["professional"])

    # 3. Verificar que la ficha del paciente existe
    pdir = BASE_DATA_PATH / payload.rut
    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Ficha del paciente {payload.rut} no encontrada"
        )

    # 4. Normalizar y grabar evento
    evento = _build_evento(payload, user, professional_name)

    with _LOCK:
        events_dir = pdir / "eventos"
        events_dir.mkdir(exist_ok=True)

        filename = f"{evento['fecha']}_{evento['hora'].replace(':','-')}.json"
        file     = events_dir / filename

        if file.exists():
            ts = datetime.now(ZoneInfo("America/Santiago")).strftime("%S")
            filename = f"{evento['fecha']}_{evento['hora'].replace(':','-')}_{ts}.json"
            file = events_dir / filename

        file.write_text(
            json.dumps(evento, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "ok":     True,
        "rut":    payload.rut,
        "evento": filename,
        "estado": "pendiente_validacion",
    }

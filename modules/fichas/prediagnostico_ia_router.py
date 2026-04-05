# modules/fichas/prediagnostico_ia_router.py
# Recibe resultado del prediagnóstico y graba evento en ICA
# Llamado desde el backend de prediagnóstico tras emitir PDF
# Profesional grabador: ia_prediagnostico (supervisor: Dr. Cristóbal Huerta Cortés)

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth
from auth.users_store import load_users
from modules.fichas.ficha_evento_create import save_clinical_event
from modules.fichas.ficha_evento_schema import FichaEventoCreate

# ============================================================
# CONFIG
# ============================================================
BASE_DATA_PATH = Path("/data/pacientes")
IA_USER_KEY    = "ia_prediagnostico"

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
# AUTH
# ============================================================
def _require_prediag_auth(x_internal_user: str = Header(None)):
    if not x_internal_user or x_internal_user != IA_USER_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")
    return require_internal_auth(x_internal_user=x_internal_user)

# ============================================================
# NORMALIZAR EVENTO
# ============================================================
def _build_evento_create(payload: PrediagnosticoPayload, ia_user: dict) -> FichaEventoCreate:
    now   = datetime.now(ZoneInfo("America/Santiago"))
    fecha = now.strftime("%Y-%m-%d")
    hora  = now.strftime("%H:%M")

    zona = payload.dolor or ""
    lado = payload.lado  or ""
    sint = f"{zona} {lado}".strip()

    examenes_txt = "\n".join(f"• {e}" for e in (payload.examenes or []) if e)
    supervisor   = ia_user.get("supervisor_display", "Dr. Cristóbal Huerta Cortés")

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
        f"Debe ser validado por {supervisor}."
    ) if payload.diagnostico else "[IA] Sin diagnóstico presuntivo"

    examenes_campo = (
        f"Exámenes sugeridos por IA (pendiente validación médica):\n{examenes_txt}"
    ) if examenes_txt else ""

    indicaciones = (
        f"Justificación clínica IA:\n{payload.justificacion}"
    ) if payload.justificacion else ""

    return FichaEventoCreate(
        rut=payload.rut,
        fecha=fecha,
        hora=hora,
        atencion=atencion,
        diagnostico=diagnostico,
        examenes=examenes_campo,
        indicaciones=indicaciones,
        receta="",
        orden_kinesiologia="",
        indicacion_quirurgica="",
    )

# ============================================================
# ENDPOINT
# ============================================================
@router.post("/registrar")
def registrar_prediagnostico(
    payload: PrediagnosticoPayload,
    x_internal_user: str = Header(None),
):
    # 1. Auth — valida y obtiene user completo
    ia_user = _require_prediag_auth(x_internal_user)

    # supervisor_display desde users.json
    users     = load_users()
    user_data = users.get(IA_USER_KEY, {})
    ia_user["supervisor_display"] = user_data.get(
        "supervisor_display", "Dr. Cristóbal Huerta Cortés"
    )

    # 2. Verificar que la ficha del paciente existe
    pdir = BASE_DATA_PATH / payload.rut
    if not pdir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Ficha del paciente {payload.rut} no encontrada"
        )

    # 3. Normalizar a FichaEventoCreate
    evento_data = _build_evento_create(payload, ia_user)

    # 4. Grabar usando save_clinical_event — mismo flujo que médicos
    result = save_clinical_event(data=evento_data, user=ia_user)

    return {
        "ok":        True,
        "rut":       payload.rut,
        "resultado": result,
        "supervisor": ia_user["supervisor_display"],
        "estado":    "pendiente_validacion",
    }
    

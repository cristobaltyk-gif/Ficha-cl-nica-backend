from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from auth.internal_auth import require_internal_auth
from db.supabase_client import get_paciente, create_evento, get_profesionales

IA_USER_KEY = "ia_prediagnostico"

router = APIRouter(
    prefix="/api/prediagnostico",
    tags=["Prediagnóstico IA"],
)


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


def _chile_now() -> str:
    return datetime.now(ZoneInfo("America/Santiago")).isoformat()


def _get_professional_name(professional_id: str) -> str:
    try:
        profesionales = get_profesionales()
        return profesionales.get(professional_id, {}).get("name", professional_id)
    except Exception:
        return professional_id


def _build_evento(payload, user, professional_name) -> dict:
    now   = datetime.now(ZoneInfo("America/Santiago"))
    fecha = now.strftime("%Y-%m-%d")
    hora  = now.strftime("%H:%M")

    zona = payload.dolor or ""
    lado = payload.lado  or ""
    sint = f"{zona} {lado}".strip()

    examenes_txt = "\n".join(f"• {e}" for e in (payload.examenes or []) if e)

    atencion = (
        f"Consulta de prediagnóstico en línea.\n"
        f"Motivo: {sint or 'No especificado'}\n"
        f"Módulo: {payload.modulo or 'trauma'}\n"
        f"ID Pago: {payload.idPago or '—'}"
    )

    return {
        "rut":                   payload.rut,
        "fecha":                 fecha,
        "hora":                  hora,
        "atencion":              atencion,
        "diagnostico":           payload.diagnostico or "",
        "examenes":              f"Exámenes sugeridos por IA:\n{examenes_txt}" if examenes_txt else "",
        "indicaciones":          payload.justificacion or "",
        "receta":                "",
        "orden_kinesiologia":    "",
        "indicacion_quirurgica": "",
        "professional_id":       user["professional"],
        "professional_user":     user["usuario"],
        "professional_role":     user["role"],
        "professional_name":     f"IA prediagnóstico · {professional_name}",
        "created_at":            _chile_now(),
    }


@router.post("/registrar")
def registrar_prediagnostico(
    payload: PrediagnosticoPayload,
    x_internal_user: str = Header(None),
):
    user = require_internal_auth(x_internal_user=x_internal_user)

    if user["usuario"] != IA_USER_KEY:
        raise HTTPException(status_code=403, detail="Sin atribuciones para este endpoint")

    if not get_paciente(payload.rut):
        raise HTTPException(
            status_code=404,
            detail=f"Ficha del paciente {payload.rut} no encontrada"
        )

    professional_name = _get_professional_name(user["professional"])
    evento = _build_evento(payload, user, professional_name)

    try:
        create_evento(payload.rut, evento)
        filename = f"{evento['fecha']}_{evento['hora'].replace(':', '-')}.json"
    except ValueError:
        # Duplicado — agregar segundos
        ts = datetime.now(ZoneInfo("America/Santiago")).strftime("%S")
        evento["hora"] = f"{evento['hora']}:{ts}"
        create_evento(payload.rut, evento)
        filename = f"{evento['fecha']}_{evento['hora'].replace(':', '-')}.json"

    return {
        "ok":     True,
        "rut":    payload.rut,
        "evento": filename,
        "estado": "pendiente_validacion",
    }

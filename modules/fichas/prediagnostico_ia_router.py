# modules/fichas/prediagnostico_ia_router.py
# Recibe resultado del prediagnóstico y crea ficha + evento en ICA
# Llamado desde el backend de prediagnóstico tras emitir PDF
# Profesional grabador: ia_prediagnostico (supervisor: Dr. Cristóbal Huerta Cortés)

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from auth.users_store import load_users
from modules.fichas.ficha_evento_create import patient_dir, LOCK, chile_now

# ============================================================
# CONFIG
# ============================================================
BASE_DATA_PATH = Path("/data/pacientes")
IA_USER_KEY    = "ia_prediagnostico"
PREDIAG_SECRET = "ica_prediag_2024"   # ← mismo valor en env del backend prediagnóstico

router = APIRouter(
    prefix="/api/prediagnostico",
    tags=["Prediagnóstico IA"],
)

# ============================================================
# SCHEMA
# ============================================================
class PrediagnosticoPayload(BaseModel):
    # Datos paciente
    rut:         str
    nombre:      str
    edad:        Optional[int]   = None
    genero:      Optional[str]   = None

    # Resultado IA
    dolor:       Optional[str]   = ""
    lado:        Optional[str]   = ""
    diagnostico: Optional[str]   = ""
    examenes:    Optional[list]  = []
    justificacion: Optional[str] = ""

    # Metadata
    idPago:      Optional[str]   = ""
    modulo:      Optional[str]   = "trauma"

# ============================================================
# AUTH SIMPLE — header secreto compartido
# ============================================================
def _require_prediag_auth(x_prediag_secret: str = Header(None)):
    if x_prediag_secret != PREDIAG_SECRET:
        raise HTTPException(status_code=401, detail="No autorizado")

def _get_ia_user():
    users = load_users()
    user  = users.get(IA_USER_KEY)
    if not user or not user.get("active"):
        raise HTTPException(
            status_code=503,
            detail="Usuario IA no configurado. Crear 'ia_prediagnostico' en el sistema."
        )
    return {
        "usuario":      IA_USER_KEY,
        "role":         user.get("role"),
        "professional": user.get("professional"),
        "supervisor":   user.get("supervisor", ""),
        "supervisor_display": user.get("supervisor_display", "Dr. Cristóbal Huerta Cortés"),
    }

# ============================================================
# HELPERS
# ============================================================
def _admin_file(rut: str) -> Path:
    return BASE_DATA_PATH / rut / "admin.json"

def _ensure_ficha_admin(payload: PrediagnosticoPayload) -> bool:
    """Crea ficha administrativa si no existe. Retorna True si la creó."""
    afile = _admin_file(payload.rut)
    if afile.exists():
        return False

    pdir = BASE_DATA_PATH / payload.rut
    pdir.mkdir(parents=True, exist_ok=True)

    nombre_parts = (payload.nombre or "").strip().split()
    nombre       = nombre_parts[0] if nombre_parts else payload.nombre
    apellido_p   = nombre_parts[1] if len(nombre_parts) > 1 else ""
    apellido_m   = nombre_parts[2] if len(nombre_parts) > 2 else ""

    ficha = {
        "rut":              payload.rut,
        "nombre":           nombre,
        "apellido_paterno": apellido_p,
        "apellido_materno": apellido_m,
        "fecha_nacimiento": "",
        "direccion":        "",
        "telefono":         "",
        "email":            "",
        "prevision":        "",
        "origen":           "prediagnostico_ia",
        "created_at":       datetime.utcnow().isoformat() + "Z",
        "updated_at":       datetime.utcnow().isoformat() + "Z",
    }
    afile.write_text(json.dumps(ficha, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def _build_evento(payload: PrediagnosticoPayload, ia_user: dict) -> dict:
    now   = datetime.now(ZoneInfo("America/Santiago"))
    fecha = now.strftime("%Y-%m-%d")
    hora  = now.strftime("%H:%M")

    zona  = payload.dolor or ""
    lado  = payload.lado  or ""
    sint  = f"{zona} {lado}".strip()

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
        f"Debe ser validado por {ia_user['supervisor_display']}."
    ) if payload.diagnostico else "[IA] Sin diagnóstico presuntivo"

    examenes_campo = (
        f"Exámenes sugeridos por IA (pendiente validación médica):\n{examenes_txt}"
    ) if examenes_txt else ""

    indicaciones = (
        f"Justificación clínica IA:\n{payload.justificacion}"
    ) if payload.justificacion else ""

    return {
        "rut":                    payload.rut,
        "fecha":                  fecha,
        "hora":                   hora,
        "atencion":               atencion,
        "diagnostico":            diagnostico,
        "examenes":               examenes_campo,
        "indicaciones":           indicaciones,
        "receta":                 "",
        "orden_kinesiologia":     "",
        "indicacion_quirurgica":  "",
        "professional_id":        ia_user["professional"],
        "professional_user":      ia_user["usuario"],
        "professional_role":      ia_user["role"],
        "supervisor":             ia_user["supervisor"],
        "supervisor_display":     ia_user["supervisor_display"],
        "origen":                 "prediagnostico_ia",
        "estado_validacion":      "pendiente",
        "created_at":             chile_now(),
    }

# ============================================================
# ENDPOINT
# ============================================================
@router.post("/registrar")
def registrar_prediagnostico(
    payload: PrediagnosticoPayload,
    x_prediag_secret: str = Header(None),
):
    _require_prediag_auth(x_prediag_secret)
    ia_user = _get_ia_user()

    with LOCK:
        # 1. Crear ficha admin si no existe
        ficha_creada = _ensure_ficha_admin(payload)

        pdir = BASE_DATA_PATH / payload.rut
        if not pdir.exists():
            raise HTTPException(status_code=500, detail="No se pudo crear directorio paciente")

        # 2. Crear evento
        evento    = _build_evento(payload, ia_user)
        events_dir = pdir / "eventos"
        events_dir.mkdir(exist_ok=True)

        filename = f"{evento['fecha']}_{evento['hora'].replace(':','-')}_ia.json"
        file     = events_dir / filename

        # Si ya existe uno en el mismo minuto, agregar sufijo
        if file.exists():
            ts = datetime.now(ZoneInfo("America/Santiago")).strftime("%S")
            filename = f"{evento['fecha']}_{evento['hora'].replace(':','-')}_{ts}_ia.json"
            file = events_dir / filename

        file.write_text(
            json.dumps(evento, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {
        "ok":          True,
        "rut":         payload.rut,
        "ficha_nueva": ficha_creada,
        "evento":      filename,
        "supervisor":  ia_user["supervisor_display"],
        "estado":      "pendiente_validacion",
    }

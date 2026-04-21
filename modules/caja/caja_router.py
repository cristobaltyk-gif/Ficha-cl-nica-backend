# ============================================================
# caja_router.py  —  PARTE 1 de 2
# Imports, constantes, helpers, schemas
# Endpoints de escritura: /config, /day, /slot (PATCH/DELETE),
#                         /pago, /anular
# ============================================================

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import io
from pathlib import Path
from datetime import datetime, date as date_type
from collections import defaultdict

from modules.caja.caja_config_helper import get_tipos_profesional, get_valor_tipo
from auth.auth_middleware import require_internal_auth

router = APIRouter(prefix="/api/caja", tags=["Caja"])

# ----------------------------------------------------------
# Rutas de datos (disco persistente de Render → /data)
# ----------------------------------------------------------
CAJA_DIR    = Path("/data/caja")
PAGOS_DIR   = Path("/data/pagos")
AGENDA_PATH = Path("/data/agenda_future.json")
CONFIG_PATH = Path(os.path.dirname(__file__)) / "caja_config.json"

# ----------------------------------------------------------
# Constantes de dominio
# ----------------------------------------------------------
TIPOS_VALIDOS = {
    "particular", "control_costo", "control_gratuito",
    "sobrecupo", "kinesiologia", "paquete_10"
}
TIPOS_GRATUITOS = {"control_gratuito"}
ESTADOS_VALIDOS = {"waiting", "paid"}
METODOS_VALIDOS = {"efectivo", "transferencia", "tarjeta"}

TIPOS_LABELS = {
    "particular":       "Particular",
    "control_costo":    "Control con costo",
    "control_gratuito": "Control gratuito",
    "sobrecupo":        "Sobrecupo",
    "kinesiologia":     "Kinesiología",
    "paquete_10":       "Paquete 10 sesiones",
}

# ----------------------------------------------------------
# Control de acceso por rol
# admin y secretaria ven todos los profesionales.
# medico y kinesiologia solo ven el suyo propio.
# ----------------------------------------------------------
ROLES_ADMIN = {"admin", "secretaria"}

def _can_see_all(auth: dict) -> bool:
    return auth["role"]["name"] in ROLES_ADMIN

def _resolve_professional(auth: dict, requested: Optional[str] = None) -> Optional[str]:
    """
    Si es admin/secretaria → devuelve `requested` tal cual (None = todos).
    Si es médico/kine      → fuerza auth['professional'], ignorando `requested`.
    """
    if _can_see_all(auth):
        return requested
    return auth["professional"]

# =========================
# HELPERS — I/O de disco
# =========================

def _month_key(date: str) -> str:
    return date[:7]

def _caja_path(date: str) -> Path:
    return CAJA_DIR / f"{_month_key(date)}.json"

def _pagos_path(date: str) -> Path:
    return PAGOS_DIR / f"{_month_key(date)}.json"

def _pagos_path_by_month(month: str) -> Path:
    return PAGOS_DIR / f"{month}.json"

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

def _load_agenda_professionals(date: str) -> List[str]:
    store = _load_json(AGENDA_PATH)
    return list(store.get("calendar", {}).get(date, {}).keys())

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

def _delete_caja_slot(date: str, professional: str, time: str) -> None:
    path  = _caja_path(date)
    store = _load_json(path)
    day   = store.get(date, {}).get(professional, {})
    if time in day:
        del day[time]
        store.setdefault(date, {})[professional] = day
        _save_json(path, store)

def _load_pagos_day(date: str, professional: str) -> dict:
    store = _load_json(_pagos_path(date))
    return store.get(date, {}).get(professional, {})

def _save_pago(date: str, professional: str, time: str, pago: dict) -> None:
    path  = _pagos_path(date)
    store = _load_json(path)
    store.setdefault(date, {}).setdefault(professional, {})[time] = pago
    _save_json(path, store)

def _format_monto(monto: int) -> str:
    return f"${monto:,}".replace(",", ".")

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

class CajaSlotDelete(BaseModel):
    date:         str
    professional: str
    time:         str

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
def get_config(professional: Optional[str] = Query(None)):
    if professional:
        return get_tipos_profesional(professional)
    config = _load_config()
    return {k: v for k, v in config.items() if k != "por_profesional"}

# =========================
# GET — panel del día
# Filtrado por rol: médico/kine solo ven su propio profesional
# =========================

@router.get("/day")
def get_caja_day(
    date: str,
    professional: str,
    auth: dict = Depends(require_internal_auth),
):
    professional = _resolve_professional(auth, professional)

    agenda_slots = _load_agenda_day(date, professional)
    caja         = _load_caja_day(date, professional)

    result = []
    for time, slot in agenda_slots.items():
        if slot.get("status") not in ("reserved", "confirmed"):
            continue
        cs    = caja.get(time, {})
        tipo  = cs.get("tipo_atencion", "particular")
        monto = get_valor_tipo(professional, tipo)
        result.append({
            "time":           time,
            "rut":            slot.get("rut", ""),
            "arrival_status": cs.get("arrival_status"),
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
        cs["tipo_atencion"] = data.tipo_atencion
        cs["monto"]         = get_valor_tipo(data.professional, data.tipo_atencion)
        cs["es_gratuito"]   = data.tipo_atencion in TIPOS_GRATUITOS
    if data.pagado is not None:
        cs["pagado"] = data.pagado

    _save_caja_slot(data.date, data.professional, data.time, cs)
    return {"ok": True, "time": data.time}

# =========================
# DELETE — limpiar slot
# =========================

@router.delete("/slot")
def delete_caja_slot(data: CajaSlotDelete):
    _delete_caja_slot(data.date, data.professional, data.time)
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

    monto = get_valor_tipo(data.professional, data.tipo_atencion)

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

    _delete_caja_slot(data.date, data.professional, data.time)
    return {"ok": True}
    # ============================================================
# caja_router.py  —  PARTE 2 de 2
# Endpoints de lectura con filtro por rol:
#   /summary, /resumen-dia, /resumen-mes, /pdf-mes
#
# PEGAR A CONTINUACIÓN DE LA PARTE 1 (mismo archivo)
# ============================================================

# =========================
# HELPER INTERNO — día sin auth
# Usado por _get_caja_summary para no llamar al endpoint con Depends
# =========================

def _get_caja_day_raw(date: str, professional: str) -> dict:
    """Versión sin auth de GET /day. Solo para llamadas internas."""
    agenda_slots = _load_agenda_day(date, professional)
    caja         = _load_caja_day(date, professional)
    result = []
    for time, slot in agenda_slots.items():
        if slot.get("status") not in ("reserved", "confirmed"):
            continue
        cs    = caja.get(time, {})
        tipo  = cs.get("tipo_atencion", "particular")
        monto = get_valor_tipo(professional, tipo)
        result.append({
            "time":           time,
            "rut":            slot.get("rut", ""),
            "arrival_status": cs.get("arrival_status"),
            "tipo_atencion":  tipo,
            "monto":          monto,
            "pagado":         cs.get("pagado", False),
            "es_gratuito":    tipo in TIPOS_GRATUITOS,
        })
    result.sort(key=lambda x: x["time"])
    return {"date": date, "professional": professional, "slots": result}


def _get_caja_summary(date: str, professional: str) -> dict:
    """Lógica pura de summary sin auth. Llamada internamente por resumen-dia."""
    day   = _get_caja_day_raw(date, professional)
    slots = day["slots"]
    pagos = _load_pagos_day(date, professional)

    total_pacientes = len(slots)
    esperando       = sum(1 for s in slots if s["arrival_status"] == "waiting" and not s["pagado"])
    pagados         = sum(1 for s in slots if s["pagado"])
    monto_total     = sum(p["monto"] for p in pagos.values() if not p.get("anulado", False))
    por_tipo        = {}
    por_metodo      = {}
    pacientes       = []

    for time, p in pagos.items():
        if p.get("anulado"):
            continue
        t = p["tipo_atencion"]
        m = p.get("metodo_pago") or "gratuito"
        por_tipo[t]   = por_tipo.get(t, 0) + 1
        por_metodo[m] = por_metodo.get(m, 0) + 1
        pacientes.append({
            "time":          time,
            "rut":           p.get("rut", ""),
            "tipo_atencion": t,
            "tipo_label":    TIPOS_LABELS.get(t, t),
            "monto":         p.get("monto", 0),
            "metodo_pago":   m,
            "es_gratuito":   p.get("es_gratuito", False),
            "pagado_at":     p.get("pagado_at"),
        })

    pacientes.sort(key=lambda x: x["time"])
    return {
        "date": date, "professional": professional,
        "total_pacientes": total_pacientes, "esperando": esperando,
        "pagados": pagados, "monto_total": monto_total,
        "por_tipo": por_tipo, "por_metodo": por_metodo, "pacientes": pacientes,
    }


def _compute_resumen_mes(month: str, professional: Optional[str] = None) -> dict:
    """
    Lógica pura de resumen mensual sin auth.
    professional=None → todos los profesionales (solo admin/secretaria llegan aquí con None).
    """
    path  = _pagos_path_by_month(month)
    store = _load_json(path)

    if not store:
        return {
            "month": month, "monto_total": 0,
            "total_pagos": 0, "total_anulados": 0,
            "por_dia": [], "por_profesional": {},
            "por_tipo": {}, "por_metodo": {}, "pagos": []
        }

    monto_total    = 0
    total_pagos    = 0
    total_anulados = 0
    por_dia        = defaultdict(int)
    por_prof       = defaultdict(lambda: {"monto": 0, "pagos": 0})
    por_tipo       = defaultdict(lambda: {"count": 0, "monto": 0})
    por_metodo     = defaultdict(lambda: {"count": 0, "monto": 0})
    pagos_list     = []

    for date_key, profs in store.items():
        for prof, slots in profs.items():
            # Filtrar por profesional si el rol lo requiere
            if professional and prof != professional:
                continue

            for time, pago in slots.items():
                if pago.get("anulado"):
                    total_anulados += 1
                    continue

                monto = pago.get("monto", 0)
                tipo  = pago.get("tipo_atencion", "")
                met   = pago.get("metodo_pago") or "gratuito"

                monto_total              += monto
                total_pagos              += 1
                por_dia[date_key]        += monto
                por_prof[prof]["monto"]  += monto
                por_prof[prof]["pagos"]  += 1
                por_tipo[TIPOS_LABELS.get(tipo, tipo)]["count"] += 1
                por_tipo[TIPOS_LABELS.get(tipo, tipo)]["monto"] += monto
                por_metodo[met]["count"] += 1
                por_metodo[met]["monto"] += monto

                pagos_list.append({
                    "date":          date_key,
                    "time":          time,
                    "professional":  prof,
                    "rut":           pago.get("rut", ""),
                    "tipo_atencion": TIPOS_LABELS.get(tipo, tipo),
                    "monto":         monto,
                    "metodo_pago":   met,
                    "es_gratuito":   pago.get("es_gratuito", False),
                    "pagado_at":     pago.get("pagado_at"),
                    "pagado_por":    pago.get("pagado_por"),
                })

    pagos_list.sort(key=lambda x: (x["date"], x["time"]))
    por_dia_list = [{"date": d, "monto": m} for d, m in sorted(por_dia.items())]

    return {
        "month":           month,
        "monto_total":     monto_total,
        "total_pagos":     total_pagos,
        "total_anulados":  total_anulados,
        "por_dia":         por_dia_list,
        "por_profesional": dict(por_prof),
        "por_tipo":        dict(por_tipo),
        "por_metodo":      dict(por_metodo),
        "pagos":           pagos_list,
    }

# =========================
# GET — resumen día (un profesional)
# =========================

@router.get("/summary")
def get_caja_summary(
    date: str,
    professional: str,
    auth: dict = Depends(require_internal_auth),
):
    professional = _resolve_professional(auth, professional)
    return _get_caja_summary(date, professional)

# =========================
# GET — resumen día (todos los profesionales)
# =========================

@router.get("/resumen-dia")
def get_resumen_dia(
    date: str,
    professional: Optional[str] = Query(None),
    auth: dict = Depends(require_internal_auth),
):
    professional  = _resolve_professional(auth, professional)
    professionals = [professional] if professional else _load_agenda_professionals(date)

    resumen_por_prof  = []
    total_global      = 0
    por_tipo_global   = {}
    por_metodo_global = {}
    pacientes_global  = []

    for prof in professionals:
        s = _get_caja_summary(date, prof)
        resumen_por_prof.append({
            "professional":    prof,
            "total_pacientes": s["total_pacientes"],
            "pagados":         s["pagados"],
            "esperando":       s["esperando"],
            "monto_total":     s["monto_total"],
        })
        total_global += s["monto_total"]
        for t, v in s["por_tipo"].items():
            por_tipo_global[t]   = por_tipo_global.get(t, 0) + v
        for m, v in s["por_metodo"].items():
            por_metodo_global[m] = por_metodo_global.get(m, 0) + v
        for p in s["pacientes"]:
            pacientes_global.append({**p, "professional": prof})

    pacientes_global.sort(key=lambda x: x["time"])
    por_tipo_labeled = {TIPOS_LABELS.get(t, t): v for t, v in por_tipo_global.items()}

    return {
        "date": date, "monto_total": total_global,
        "por_tipo": por_tipo_labeled, "por_metodo": por_metodo_global,
        "por_profesional": resumen_por_prof, "pacientes": pacientes_global,
    }

# =========================
# GET — resumen mensual (contable)
# =========================

@router.get("/resumen-mes")
def get_resumen_mes(
    month: str,
    auth: dict = Depends(require_internal_auth),
):
    professional = _resolve_professional(auth)
    return _compute_resumen_mes(month, professional)

# =========================
# GET — exportar PDF mensual
# Médico/kine → PDF solo con sus datos + nombre de archivo personalizado
# Admin/secretaria → PDF con todos los profesionales
# =========================

@router.get("/pdf-mes")
def get_pdf_mes(
    month: str,
    auth: dict = Depends(require_internal_auth),
):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab no instalado")

    professional = _resolve_professional(auth)
    data         = _compute_resumen_mes(month, professional)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    title_style   = ParagraphStyle("title",   parent=styles["Heading1"], fontSize=16, spaceAfter=4,  alignment=TA_CENTER)
    sub_style     = ParagraphStyle("sub",     parent=styles["Normal"],   fontSize=10, spaceAfter=12, alignment=TA_CENTER, textColor=colors.grey)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=6)

    subtitle = f"Resumen contable — {month}"
    if professional:
        subtitle += f" — {professional}"

    story.append(Paragraph("Instituto de Cirugía Articular", title_style))
    story.append(Paragraph(subtitle, sub_style))
    story.append(Spacer(1, 0.3*cm))

    # KPIs
    kpi_data = [
        ["Total recaudado", "Total pagos", "Anulados"],
        [_format_monto(data["monto_total"]), str(data["total_pagos"]), str(data["total_anulados"])]
    ]
    kpi_table = Table(kpi_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
        ("FONTSIZE",       (0,0), (-1,0), 10),
        ("FONTSIZE",       (0,1), (-1,1), 13),
        ("FONTNAME",       (0,1), (-1,1), "Helvetica-Bold"),
        ("ALIGN",          (0,0), (-1,-1), "CENTER"),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f8fafc")]),
        ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWHEIGHT",      (0,0), (-1,-1), 28),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # Tabla por profesional: solo visible para admin/secretaria
    if not professional:
        story.append(Paragraph("Por profesional", section_style))
        prof_data = [["Profesional", "Pagos", "Total"]]
        for prof, vals in data["por_profesional"].items():
            prof_data.append([prof, str(vals["pagos"]), _format_monto(vals["monto"])])
        prof_table = Table(prof_data, colWidths=[8*cm, 4*cm, 4.5*cm])
        prof_table.setStyle(TableStyle([
            ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
            ("FONTSIZE",       (0,0), (-1,-1), 9),
            ("ALIGN",          (1,0), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f6ff")]),
            ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWHEIGHT",      (0,0), (-1,-1), 22),
        ]))
        story.append(prof_table)

    # Por tipo de atención
    story.append(Paragraph("Por tipo de atención", section_style))
    tipo_data = [["Tipo", "Cantidad", "Total"]]
    for tipo, vals in data["por_tipo"].items():
        tipo_data.append([tipo, str(vals["count"]), _format_monto(vals["monto"])])
    tipo_table = Table(tipo_data, colWidths=[8*cm, 4*cm, 4.5*cm])
    tipo_table.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
        ("FONTSIZE",       (0,0), (-1,-1), 9),
        ("ALIGN",          (1,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWHEIGHT",      (0,0), (-1,-1), 22),
    ]))
    story.append(tipo_table)

    # Por método de pago
    story.append(Paragraph("Por método de pago", section_style))
    met_data = [["Método", "Cantidad", "Total"]]
    for met, vals in data["por_metodo"].items():
        met_data.append([met.capitalize(), str(vals["count"]), _format_monto(vals["monto"])])
    met_table = Table(met_data, colWidths=[8*cm, 4*cm, 4.5*cm])
    met_table.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
        ("FONTSIZE",       (0,0), (-1,-1), 9),
        ("ALIGN",          (1,0), (-1,-1), "CENTER"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWHEIGHT",      (0,0), (-1,-1), 22),
    ]))
    story.append(met_table)

    # Detalle de pagos
    story.append(Paragraph("Detalle de pagos", section_style))
    det_data = [["Fecha", "Hora", "Profesional", "RUT", "Tipo", "Método", "Monto"]]
    for p in data["pagos"]:
        det_data.append([
            p["date"], p["time"], p["professional"],
            p["rut"], p["tipo_atencion"],
            p["metodo_pago"].capitalize() if p["metodo_pago"] else "Gratuito",
            _format_monto(p["monto"]),
        ])
    det_table = Table(det_data, colWidths=[2.2*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.8*cm, 2.2*cm, 2.8*cm])
    det_table.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR",      (0,0), (-1,0), colors.white),
        ("FONTSIZE",       (0,0), (-1,-1), 7),
        ("ALIGN",          (6,0), (6,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",           (0,0), (-1,-1), 0.3, colors.HexColor("#e2e8f0")),
        ("ROWHEIGHT",      (0,0), (-1,-1), 18),
    ]))
    story.append(det_table)

    doc.build(story)
    buf.seek(0)

    filename = f"caja_{month}_{professional}.pdf" if professional else f"caja_{month}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
)
    

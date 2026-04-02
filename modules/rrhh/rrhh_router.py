"""
modules/rrhh/rrhh_router.py
Gestión de remuneraciones — trabajadores, liquidaciones, tasas legales.
Solo visible para administración.
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/rrhh", tags=["RRHH"])

TRABAJADORES_PATH = Path("/data/rrhh/trabajadores.json")
TASAS_PATH        = Path("/data/rrhh/tasas.json")
LOCK              = Lock()

# ======================================================
# TASAS LEGALES VIGENTES CHILE 2024
# ======================================================

DEFAULT_TASAS = {
    "afp": {
        "capital":    0.1130,
        "cuprum":     0.1144,
        "habitat":    0.1127,
        "modelo":     0.1058,
        "planvital":  0.1116,
        "provida":    0.1145,
        "uno":        0.1069,
    },
    "sis": 0.0187,               # Seguro Invalidez y Sobrevivencia (empleador)
    "salud_trabajador": 0.07,    # 7% salud trabajador
    "fonasa_adicional": 0.0,     # sin adicional Fonasa
    "afc_trabajador_indefinido":  0.006,   # AFC trabajador contrato indefinido
    "afc_trabajador_plazo_fijo":  0.011,   # AFC trabajador plazo fijo
    "afc_empleador_indefinido":   0.0236,  # AFC empleador contrato indefinido
    "afc_empleador_plazo_fijo":   0.03,    # AFC empleador plazo fijo
    "mutual":                     0.0093,  # Mutual de Seguridad (empleador)
    "utm": 66461,                          # UTM vigente CLP
    "tramos_impuesto": [
        {"desde": 0,      "hasta": 934_234,   "tasa": 0.00,  "rebaja": 0},
        {"desde": 934_234, "hasta": 2_075_076, "tasa": 0.04, "rebaja": 37_369},
        {"desde": 2_075_076, "hasta": 3_458_460, "tasa": 0.08, "rebaja": 120_373},
        {"desde": 3_458_460, "hasta": 4_841_844, "tasa": 0.135, "rebaja": 310_594},
        {"desde": 4_841_844, "hasta": 6_225_228, "tasa": 0.23,  "rebaja": 770_568},
        {"desde": 6_225_228, "hasta": 8_302_972, "tasa": 0.304, "rebaja": 1_231_505},
        {"desde": 8_302_972, "hasta": 999_999_999, "tasa": 0.35, "rebaja": 1_613_047},
    ]
}

TIPOS_CONTRATO = ["indefinido", "plazo_fijo", "honorarios"]
CARGOS = ["Secretaria", "Kinesiólogo", "Personal de aseo", "Guardia", "Recepcionista", "Otro"]


# ======================================================
# HELPERS
# ======================================================

def _load_trabajadores() -> dict:
    if not TRABAJADORES_PATH.exists():
        return {}
    with open(TRABAJADORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_trabajadores(data: dict) -> None:
    TRABAJADORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRABAJADORES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_tasas() -> dict:
    if not TASAS_PATH.exists():
        TASAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TASAS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_TASAS, f, indent=2, ensure_ascii=False)
        return DEFAULT_TASAS
    with open(TASAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _clp(n: float) -> int:
    return int(round(n))


def calcular_liquidacion(trabajador: dict, tasas: dict, mes: str) -> dict:
    """
    Calcula la liquidación de sueldo completa según leyes chilenas.
    """
    tipo         = trabajador.get("tipo_contrato", "indefinido")
    sueldo_base  = trabajador.get("sueldo_base", 0)
    afp_nombre   = trabajador.get("afp", "habitat").lower()
    isapre       = trabajador.get("isapre", False)
    monto_isapre = trabajador.get("monto_isapre", 0)  # monto adicional isapre sobre 7%

    if tipo == "honorarios":
        # Honorarios: 10.75% retención sobre boleta
        retencion    = _clp(sueldo_base * 0.1075)
        liquido      = sueldo_base - retencion
        return {
            "trabajador_id":  trabajador["id"],
            "nombre":         trabajador["nombre"],
            "tipo_contrato":  tipo,
            "mes":            mes,
            "sueldo_base":    sueldo_base,
            "retencion_boleta": retencion,
            "liquido":        liquido,
            "costo_empresa":  sueldo_base,
            "es_honorarios":  True,
        }

    # ── DESCUENTOS TRABAJADOR ──
    tasa_afp     = tasas["afp"].get(afp_nombre, 0.1127)
    descuento_afp = _clp(sueldo_base * tasa_afp)

    descuento_salud = _clp(sueldo_base * tasas["salud_trabajador"])
    if isapre and monto_isapre > descuento_salud:
        descuento_salud = monto_isapre  # isapre cobra más que el 7%

    afc_trab = tasas["afc_trabajador_indefinido"] if tipo == "indefinido" else tasas["afc_trabajador_plazo_fijo"]
    descuento_afc = _clp(sueldo_base * afc_trab)

    total_descuentos_prevision = descuento_afp + descuento_salud + descuento_afc

    # ── BASE IMPONIBLE IMPUESTO ──
    base_imponible = sueldo_base - total_descuentos_prevision
    impuesto = _calcular_impuesto(base_imponible, tasas["tramos_impuesto"])

    total_descuentos = total_descuentos_prevision + impuesto
    liquido          = sueldo_base - total_descuentos

    # ── COSTO EMPRESA ──
    sis      = _clp(sueldo_base * tasas["sis"])
    mutual   = _clp(sueldo_base * tasas["mutual"])
    afc_emp  = _clp(sueldo_base * (
        tasas["afc_empleador_indefinido"] if tipo == "indefinido"
        else tasas["afc_empleador_plazo_fijo"]
    ))
    costo_empresa = sueldo_base + sis + mutual + afc_emp

    return {
        "trabajador_id":          trabajador["id"],
        "nombre":                 trabajador["nombre"],
        "rut":                    trabajador.get("rut", ""),
        "cargo":                  trabajador.get("cargo", ""),
        "tipo_contrato":          tipo,
        "afp":                    afp_nombre.capitalize(),
        "salud":                  "Isapre" if isapre else "Fonasa",
        "mes":                    mes,
        "sueldo_base":            sueldo_base,
        "descuento_afp":          descuento_afp,
        "descuento_salud":        descuento_salud,
        "descuento_afc":          descuento_afc,
        "impuesto_unico":         impuesto,
        "total_descuentos":       total_descuentos,
        "liquido":                liquido,
        "costo_sis":              sis,
        "costo_mutual":           mutual,
        "costo_afc_empleador":    afc_emp,
        "costo_empresa":          costo_empresa,
        "es_honorarios":          False,
    }


def _calcular_impuesto(base: int, tramos: list) -> int:
    for t in reversed(tramos):
        if base > t["desde"]:
            impuesto = base * t["tasa"] - t["rebaja"]
            return max(_clp(impuesto), 0)
    return 0


# ======================================================
# SCHEMAS
# ======================================================

class TrabajadorCreate(BaseModel):
    nombre:          str
    rut:             str
    cargo:           str
    tipo_contrato:   str
    sueldo_base:     int
    afp:             str = "habitat"
    isapre:          bool = False
    monto_isapre:    int = 0
    activo:          bool = True

class TrabajadorUpdate(BaseModel):
    nombre:          Optional[str] = None
    cargo:           Optional[str] = None
    tipo_contrato:   Optional[str] = None
    sueldo_base:     Optional[int] = None
    afp:             Optional[str] = None
    isapre:          Optional[bool] = None
    monto_isapre:    Optional[int] = None
    activo:          Optional[bool] = None


# ======================================================
# TASAS
# ======================================================

@router.get("/tasas")
def get_tasas():
    return _load_tasas()


@router.put("/tasas")
def update_tasas(data: dict):
    with LOCK:
        tasas = _load_tasas()
        tasas.update(data)
        with open(TASAS_PATH, "w", encoding="utf-8") as f:
            json.dump(tasas, f, indent=2, ensure_ascii=False)
    return {"ok": True}


# ======================================================
# TRABAJADORES
# ======================================================

@router.get("/trabajadores")
def list_trabajadores():
    return list(_load_trabajadores().values())


@router.post("/trabajadores")
def create_trabajador(data: TrabajadorCreate):
    with LOCK:
        trabajadores = _load_trabajadores()
        tid = data.rut.replace(".", "").replace("-", "")
        if tid in trabajadores:
            raise HTTPException(status_code=409, detail="Trabajador ya existe")
        trabajadores[tid] = {
            "id":            tid,
            "nombre":        data.nombre,
            "rut":           data.rut,
            "cargo":         data.cargo,
            "tipo_contrato": data.tipo_contrato,
            "sueldo_base":   data.sueldo_base,
            "afp":           data.afp,
            "isapre":        data.isapre,
            "monto_isapre":  data.monto_isapre,
            "activo":        data.activo,
            "created_at":    datetime.now().isoformat(timespec="seconds")
        }
        _save_trabajadores(trabajadores)
    return trabajadores[tid]


@router.put("/trabajadores/{tid}")
def update_trabajador(tid: str, data: TrabajadorUpdate):
    with LOCK:
        trabajadores = _load_trabajadores()
        if tid not in trabajadores:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")
        for k, v in data.dict(exclude_none=True).items():
            trabajadores[tid][k] = v
        _save_trabajadores(trabajadores)
        return trabajadores[tid]


@router.delete("/trabajadores/{tid}")
def delete_trabajador(tid: str):
    with LOCK:
        trabajadores = _load_trabajadores()
        if tid not in trabajadores:
            raise HTTPException(status_code=404, detail="Trabajador no encontrado")
        del trabajadores[tid]
        _save_trabajadores(trabajadores)
    return {"ok": True}


# ======================================================
# LIQUIDACIONES
# ======================================================

@router.get("/liquidacion/{tid}/{mes}")
def get_liquidacion(tid: str, mes: str):
    trabajadores = _load_trabajadores()
    if tid not in trabajadores:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    tasas = _load_tasas()
    return calcular_liquidacion(trabajadores[tid], tasas, mes)


@router.get("/liquidaciones/{mes}")
def get_liquidaciones_mes(mes: str):
    """Calcula todas las liquidaciones del mes y registra en gastos contables."""
    trabajadores = _load_trabajadores()
    tasas        = _load_tasas()

    activos = [t for t in trabajadores.values() if t.get("activo", True)]
    liqds   = [calcular_liquidacion(t, tasas, mes) for t in activos]

    total_liquidos       = sum(l["liquido"] for l in liqds)
    total_costo_empresa  = sum(l["costo_empresa"] for l in liqds)
    total_descuentos     = sum(l.get("total_descuentos", l.get("retencion_boleta", 0)) for l in liqds)

    return {
        "mes":                mes,
        "trabajadores":       len(liqds),
        "liquidaciones":      liqds,
        "total_liquidos":     total_liquidos,
        "total_descuentos":   total_descuentos,
        "total_costo_empresa": total_costo_empresa,
    }


@router.post("/liquidaciones/{mes}/registrar-gasto")
def registrar_gasto_sueldos(mes: str):
    """Registra el total de sueldos del mes en gastos contables."""
    data = get_liquidaciones_mes(mes)

    import httpx, os
    backend = os.getenv("BACKEND_URL", "http://localhost:10000")

    # Eliminar gasto anterior de sueldos del mismo mes si existe
    # Registrar nuevo
    try:
        httpx.post(f"{backend}/api/contable/gastos", json={
            "mes":         mes,
            "grupo":       "fijos",
            "categoria":   "Sueldos",
            "descripcion": f"Remuneraciones {mes} — {data['trabajadores']} trabajadores",
            "monto":       data["total_costo_empresa"]
        }, timeout=10)
    except:
        pass

    return {"ok": True, "monto": data["total_costo_empresa"]}


# ======================================================
# PDF LIQUIDACIÓN
# ======================================================

@router.get("/liquidacion/{tid}/{mes}/pdf")
def pdf_liquidacion(tid: str, mes: str):
    trabajadores = _load_trabajadores()
    if tid not in trabajadores:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    tasas = _load_tasas()
    liq   = calcular_liquidacion(trabajadores[tid], tasas, mes)
    buf   = io.BytesIO()
    _generar_pdf_liquidacion(liq, buf)
    buf.seek(0)

    nombre = liq["nombre"].replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=liquidacion_{nombre}_{mes}.pdf"}
    )


def _generar_pdf_liquidacion(liq: dict, buffer: io.BytesIO):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    NAVY  = colors.HexColor("#0D1B2A")
    GRAY  = colors.HexColor("#F1F5F9")
    GREEN = colors.HexColor("#166534")
    RED   = colors.HexColor("#991B1B")

    title_style = ParagraphStyle("t", parent=styles["Normal"],
                                 fontSize=16, fontName="Helvetica-Bold",
                                 textColor=colors.white, alignment=TA_CENTER)
    sub_style   = ParagraphStyle("s", parent=styles["Normal"],
                                 fontSize=10, textColor=colors.HexColor("#64748b"),
                                 alignment=TA_CENTER, spaceAfter=16)
    label_style = ParagraphStyle("l", parent=styles["Normal"],
                                 fontSize=9, fontName="Helvetica-Bold",
                                 textColor=colors.HexColor("#374151"))
    val_style   = ParagraphStyle("v", parent=styles["Normal"],
                                 fontSize=9, alignment=TA_RIGHT)

    def clp(n):
        return f"${int(n):,}".replace(",", ".")

    def row(label, valor, color=None):
        return [
            Paragraph(label, label_style),
            Paragraph(f'<font color="{"#991b1b" if color=="red" else "#166534" if color=="green" else "#0f172a"}">{valor}</font>', val_style)
        ]

    # Header
    header_table = Table([[Paragraph("LIQUIDACIÓN DE SUELDO", title_style)]], colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("ROUNDEDCORNERS", [6]),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Instituto de Cirugía Articular — {liq['mes']}", sub_style))

    # Datos trabajador
    info_data = [
        [Paragraph("<b>Trabajador</b>", label_style), Paragraph(liq["nombre"], val_style)],
        [Paragraph("<b>RUT</b>",         label_style), Paragraph(liq.get("rut",""), val_style)],
        [Paragraph("<b>Cargo</b>",        label_style), Paragraph(liq.get("cargo",""), val_style)],
        [Paragraph("<b>Contrato</b>",     label_style), Paragraph(liq["tipo_contrato"].capitalize(), val_style)],
    ]
    if not liq.get("es_honorarios"):
        info_data += [
            [Paragraph("<b>AFP</b>",   label_style), Paragraph(liq.get("afp",""), val_style)],
            [Paragraph("<b>Salud</b>", label_style), Paragraph(liq.get("salud",""), val_style)],
        ]

    info_table = Table(info_data, colWidths=[8*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GRAY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, GRAY]),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    if liq.get("es_honorarios"):
        liq_data = [
            row("Monto bruto boleta",       clp(liq["sueldo_base"])),
            row("Retención 10.75%",          clp(liq["retencion_boleta"]), "red"),
            row("TOTAL LÍQUIDO A PAGAR",    clp(liq["liquido"]), "green"),
        ]
    else:
        liq_data = [
            row("Sueldo base",              clp(liq["sueldo_base"])),
            row(f"AFP ({liq.get('afp','')})", f"({clp(liq['descuento_afp'])})", "red"),
            row("Salud",                    f"({clp(liq['descuento_salud'])})", "red"),
            row("AFC trabajador",           f"({clp(liq['descuento_afc'])})", "red"),
            row("Impuesto único 2ª cat.",   f"({clp(liq['impuesto_unico'])})", "red"),
            row("Total descuentos",         f"({clp(liq['total_descuentos'])})", "red"),
            row("SUELDO LÍQUIDO",           clp(liq["liquido"]), "green"),
        ]

    liq_table = Table(liq_data, colWidths=[10*cm, 7*cm])
    liq_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-2), [colors.white, GRAY]),
        ("BACKGROUND",     (0,-1), (-1,-1), colors.HexColor("#F0FDF4")),
        ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ("FONTNAME",       (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TOPPADDING",     (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 7),
        ("LEFTPADDING",    (0,0), (-1,-1), 10),
        ("RIGHTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(liq_table)

    if not liq.get("es_honorarios"):
        story.append(Spacer(1, 0.4*cm))
        costo_data = [
            row("Sueldo base",            clp(liq["sueldo_base"])),
            row("SIS (empleador)",         clp(liq["costo_sis"])),
            row("Mutual (empleador)",      clp(liq["costo_mutual"])),
            row("AFC empleador",           clp(liq["costo_afc_empleador"])),
            row("COSTO TOTAL EMPRESA",     clp(liq["costo_empresa"]), "green"),
        ]
        cost_table = Table(costo_data, colWidths=[10*cm, 7*cm])
        cost_table.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0,0), (-1,-2), [colors.white, GRAY]),
            ("BACKGROUND",     (0,-1), (-1,-1), colors.HexColor("#EFF6FF")),
            ("GRID",           (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ("FONTNAME",       (0,-1), (-1,-1), "Helvetica-Bold"),
            ("TOPPADDING",     (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 7),
            ("LEFTPADDING",    (0,0), (-1,-1), 10),
            ("RIGHTPADDING",   (0,0), (-1,-1), 10),
        ]))
        story.append(Paragraph("Costo empresa", ParagraphStyle("h", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica-Bold", textColor=NAVY, spaceBefore=8, spaceAfter=4)))
        story.append(cost_table)

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        "Instituto de Cirugía Articular · Curicó, Chile",
        ParagraphStyle("f", parent=styles["Normal"], fontSize=8,
                       textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER)
    ))

    doc.build(story)


# ======================================================
# EXCEL RESUMEN MES
# ======================================================

@router.get("/liquidaciones/{mes}/excel")
def excel_liquidaciones(mes: str):
    data = get_liquidaciones_mes(mes)
    buf  = io.BytesIO()
    _generar_excel_liquidaciones(data, buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=remuneraciones_{mes}.xlsx"}
    )


def _generar_excel_liquidaciones(data: dict, buffer: io.BytesIO):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = f"Remuneraciones {data['mes']}"
    ws.sheet_view.showGridLines = False

    NAVY   = "0D1B2A"
    GRAY   = "F1F5F9"
    GREEN  = "F0FDF4"
    BLUE   = "EFF6FF"
    RED    = "FEF2F2"

    def hf(color="FFFFFF", bold=True, size=10):
        return Font(name="Arial", bold=bold, color=color, size=size)

    def fill(c):
        return PatternFill("solid", start_color=c, fgColor=c)

    def border():
        t = Side(style="thin", color="E2E8F0")
        return Border(left=t, right=t, top=t, bottom=t)

    def center():
        return Alignment(horizontal="center", vertical="center")

    # Título
    ws.merge_cells("A1:N1")
    ws["A1"] = f"Instituto de Cirugía Articular — Remuneraciones {data['mes']}"
    ws["A1"].font      = Font(name="Arial", bold=True, size=14, color=NAVY)
    ws["A1"].alignment = center()
    ws.row_dimensions[1].height = 32

    # KPIs fila 3
    kpis = [
        ("Trabajadores", data["trabajadores"], GRAY),
        ("Total líquido", data["total_liquidos"], "F0FDF4"),
        ("Total descuentos", data["total_descuentos"], "FEF2F2"),
        ("Costo empresa", data["total_costo_empresa"], "EFF6FF"),
    ]
    for i, (label, val, bg) in enumerate(kpis):
        col = i * 2 + 1
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col+1)
        ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col+1)
        c1 = ws.cell(row=3, column=col, value=label)
        c1.font = Font(name="Arial", size=9, bold=True, color="64748B")
        c1.alignment = center()
        c1.fill = fill(bg)
        c1.border = border()
        c2 = ws.cell(row=4, column=col, value=val)
        c2.font = Font(name="Arial", size=14, bold=True, color=NAVY)
        c2.alignment = center()
        c2.fill = fill(bg)
        c2.border = border()
        c2.number_format = "$#,##0;($#,##0);\"-\""

    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 30

    # Headers tabla
    headers = ["Nombre", "RUT", "Cargo", "Contrato", "AFP", "Salud",
               "Sueldo Base", "AFP", "Salud", "AFC", "Imp. Único",
               "Total Desc.", "Líquido", "Costo Empresa"]

    for j, h in enumerate(headers):
        c = ws.cell(row=6, column=j+1, value=h)
        c.font      = hf()
        c.fill      = fill(NAVY)
        c.alignment = center()
        c.border    = border()
    ws.row_dimensions[6].height = 22

    # Datos
    for i, liq in enumerate(data["liquidaciones"]):
        row_n = i + 7
        bg    = "FFFFFF" if i % 2 == 0 else GRAY

        if liq.get("es_honorarios"):
            vals = [
                liq["nombre"], liq.get("rut",""), liq.get("cargo",""),
                "Honorarios", "-", "-",
                liq["sueldo_base"], "-", "-", "-", "-",
                liq["retencion_boleta"], liq["liquido"], liq["sueldo_base"]
            ]
        else:
            vals = [
                liq["nombre"], liq.get("rut",""), liq.get("cargo",""),
                liq["tipo_contrato"].capitalize(), liq.get("afp",""), liq.get("salud",""),
                liq["sueldo_base"],
                -liq["descuento_afp"], -liq["descuento_salud"],
                -liq["descuento_afc"], -liq["impuesto_unico"],
                -liq["total_descuentos"], liq["liquido"], liq["costo_empresa"]
            ]

        for j, v in enumerate(vals):
            c = ws.cell(row=row_n, column=j+1, value=v)
            c.font   = Font(name="Arial", size=9)
            c.fill   = fill(bg)
            c.border = border()
            if j >= 6 and isinstance(v, (int, float)):
                c.number_format = "$#,##0;($#,##0);\"-\""
                if v < 0:
                    c.font = Font(name="Arial", size=9, color="991B1B")
                elif j == 12:
                    c.font = Font(name="Arial", size=9, bold=True, color="166534")
                elif j == 13:
                    c.font = Font(name="Arial", size=9, bold=True, color="1E40AF")

    # Totales
    total_row = len(data["liquidaciones"]) + 7
    ws.cell(row=total_row, column=12, value="TOTALES").font = Font(name="Arial", bold=True, size=10)
    ws.cell(row=total_row, column=12).fill   = fill(GRAY)
    ws.cell(row=total_row, column=12).border = border()

    for col, val in [(13, data["total_liquidos"]), (14, data["total_costo_empresa"])]:
        c = ws.cell(row=total_row, column=col, value=val)
        c.font          = Font(name="Arial", bold=True, size=11, color=NAVY)
        c.number_format = "$#,##0;($#,##0);\"-\""
        c.fill          = fill(GRAY)
        c.border        = border()

    # Anchos columnas
    widths = [22, 12, 16, 12, 10, 8, 12, 10, 10, 10, 10, 12, 12, 14]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65+i)].width = w

        buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=remuneraciones_{mes}.xlsx"}
    )


def _generar_excel_liquidaciones(data: dict, buffer: io.BytesIO):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = f"Remuneraciones {data['mes']}"
    ws.sheet_view.showGridLines = False

    NAVY  = "0D1B2A"
    GRAY  = "F1F5F9"

    def hf(color="FFFFFF", bold=True, size=10):
        return Font(name="Arial", bold=bold, color=color, size=size)

    def fill(c):
        return PatternFill("solid", start_color=c, fgColor=c)

    def brd():
        t = Side(style="thin", color="E2E8F0")
        return Border(left=t, right=t, top=t, bottom=t)

    def center():
        return Alignment(horizontal="center", vertical="center")

    # Título
    ws.merge_cells("A1:N1")
    ws["A1"] = f"Instituto de Cirugía Articular — Remuneraciones {data['mes']}"
    ws["A1"].font      = Font(name="Arial", bold=True, size=14, color=NAVY)
    ws["A1"].alignment = center()
    ws.row_dimensions[1].height = 32

    # KPIs fila 3-4
    kpis = [
        ("Trabajadores",    data["trabajadores"],          "F1F5F9"),
        ("Total líquido",   data["total_liquidos"],         "F0FDF4"),
        ("Total descuentos", data["total_descuentos"],      "FEF2F2"),
        ("Costo empresa",   data["total_costo_empresa"],    "EFF6FF"),
    ]
    for i, (label, val, bg) in enumerate(kpis):
        col = i * 2 + 1
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col+1)
        ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col+1)
        c1 = ws.cell(row=3, column=col, value=label)
        c1.font = Font(name="Arial", size=9, bold=True, color="64748B")
        c1.alignment = center()
        c1.fill = fill(bg)
        c1.border = brd()
        c2 = ws.cell(row=4, column=col, value=val)
        c2.font = Font(name="Arial", size=14, bold=True, color=NAVY)
        c2.alignment = center()
        c2.fill = fill(bg)
        c2.border = brd()
        c2.number_format = "$#,##0;($#,##0);\"-\""

    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 30

    # Headers
    headers = ["Nombre", "RUT", "Cargo", "Contrato", "AFP", "Salud",
               "Sueldo Base", "AFP", "Salud", "AFC", "Imp. Único",
               "Total Desc.", "Líquido", "Costo Empresa"]

    for j, h in enumerate(headers):
        c = ws.cell(row=6, column=j+1, value=h)
        c.font      = hf()
        c.fill      = fill(NAVY)
        c.alignment = center()
        c.border    = brd()
    ws.row_dimensions[6].height = 22

    # Datos
    for i, liq in enumerate(data["liquidaciones"]):
        row_n = i + 7
        bg    = "FFFFFF" if i % 2 == 0 else GRAY

        if liq.get("es_honorarios"):
            vals = [
                liq["nombre"], liq.get("rut",""), liq.get("cargo",""),
                "Honorarios", "-", "-",
                liq["sueldo_base"], "-", "-", "-", "-",
                liq["retencion_boleta"], liq["liquido"], liq["sueldo_base"]
            ]
        else:
            vals = [
                liq["nombre"], liq.get("rut",""), liq.get("cargo",""),
                liq["tipo_contrato"].capitalize(), liq.get("afp",""), liq.get("salud",""),
                liq["sueldo_base"],
                -liq["descuento_afp"], -liq["descuento_salud"],
                -liq["descuento_afc"], -liq["impuesto_unico"],
                -liq["total_descuentos"], liq["liquido"], liq["costo_empresa"]
            ]

        for j, v in enumerate(vals):
            c = ws.cell(row=row_n, column=j+1, value=v)
            c.font   = Font(name="Arial", size=9)
            c.fill   = fill(bg)
            c.border = brd()
            if j >= 6 and isinstance(v, (int, float)):
                c.number_format = "$#,##0;($#,##0);\"-\""
                if v < 0:
                    c.font = Font(name="Arial", size=9, color="991B1B")
                elif j == 12:
                    c.font = Font(name="Arial", size=9, bold=True, color="166534")
                elif j == 13:
                    c.font = Font(name="Arial", size=9, bold=True, color="1E40AF")

    # Totales
    total_row = len(data["liquidaciones"]) + 7
    ws.cell(row=total_row, column=12, value="TOTALES").font = Font(name="Arial", bold=True, size=10)
    ws.cell(row=total_row, column=12).fill   = fill(GRAY)
    ws.cell(row=total_row, column=12).border = brd()

    for col, val in [(13, data["total_liquidos"]), (14, data["total_costo_empresa"])]:
        c = ws.cell(row=total_row, column=col, value=val)
        c.font          = Font(name="Arial", bold=True, size=11, color=NAVY)
        c.number_format = "$#,##0;($#,##0);\"-\""
        c.fill          = fill(GRAY)
        c.border        = brd()

    # Anchos columnas
    widths = [22, 12, 16, 12, 10, 8, 12, 10, 10, 10, 10, 12, 12, 14]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65+i)].width = w

    wb.save(buffer)
    

"""
modules/contable/contable_router.py
Resumen financiero consolidado + exportar Excel.
"""

from __future__ import annotations

import json
import io
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from auth.internal_auth import require_internal_auth

router = APIRouter(prefix="/api/contable", tags=["Contable"])

GASTOS_PATH = Path("/data/gastos.json")
PAGOS_DIR   = Path("/data/pagos")

TIPOS_LABELS = {
    "particular":       "Particular",
    "control_costo":    "Control con costo",
    "control_gratuito": "Control gratuito",
    "sobrecupo":        "Sobrecupo",
    "cortesia":         "Cortesía",
    "kinesiologia":     "Kinesiología",
}

GRUPOS_LABELS = {
    "fijos":     "Gastos Fijos",
    "variables": "Gastos Variables",
    "cuentas":   "Cuentas",
}


def _load_gastos() -> dict:
    if not GASTOS_PATH.exists():
        return {}
    with open(GASTOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_pagos_mes(mes: str) -> list:
    path = PAGOS_DIR / f"{mes}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pagos = []
    for fecha, profs in data.items():
        for prof, slots in profs.items():
            for time, pago in slots.items():
                pagos.append({**pago, "fecha": fecha, "time": time, "professional": prof})
    return pagos


def _resumen_mes(mes: str) -> dict:
    pagos  = _load_pagos_mes(mes)
    gastos = _load_gastos().get(mes, {})

    ingresos_total   = 0
    anulados_total   = 0
    ingresos_detalle = []
    anulados_detalle = []

    for p in pagos:
        monto = p.get("monto", 0)
        if p.get("anulado"):
            anulados_total += monto
            anulados_detalle.append({
                "fecha":        p["fecha"],
                "time":         p["time"],
                "rut":          p.get("rut", ""),
                "tipo":         TIPOS_LABELS.get(p.get("tipo_atencion", ""), p.get("tipo_atencion", "")),
                "monto":        -monto,
                "motivo":       p.get("anulacion_motivo", ""),
                "professional": p["professional"]
            })
        else:
            ingresos_total += monto
            ingresos_detalle.append({
                "fecha":        p["fecha"],
                "time":         p["time"],
                "rut":          p.get("rut", ""),
                "tipo":         TIPOS_LABELS.get(p.get("tipo_atencion", ""), p.get("tipo_atencion", "")),
                "monto":        monto,
                "metodo":       p.get("metodo_pago") or "gratuito",
                "es_gratuito":  p.get("es_gratuito", False),
                "professional": p["professional"]
            })

    gastos_total     = 0
    gastos_detalle   = []
    gastos_por_grupo = {}

    for grupo, items in gastos.items():
        grupo_total = 0
        for gasto in items:
            monto = gasto.get("monto", 0)
            gastos_total += monto
            grupo_total  += monto
            gastos_detalle.append({
                "id":          gasto["id"],
                "grupo":       GRUPOS_LABELS.get(grupo, grupo),
                "categoria":   gasto["categoria"],
                "descripcion": gasto.get("descripcion", ""),
                "monto":       -monto,
                "created_at":  gasto.get("created_at", "")
            })
        gastos_por_grupo[GRUPOS_LABELS.get(grupo, grupo)] = grupo_total

    utilidad_neta = ingresos_total - anulados_total - gastos_total

    return {
        "mes":              mes,
        "ingresos_total":   ingresos_total,
        "anulados_total":   anulados_total,
        "gastos_total":     gastos_total,
        "utilidad_neta":    utilidad_neta,
        "ingresos":         sorted(ingresos_detalle, key=lambda x: (x["fecha"], x["time"])),
        "anulados":         sorted(anulados_detalle,  key=lambda x: (x["fecha"], x["time"])),
        "gastos":           sorted(gastos_detalle,    key=lambda x: x["created_at"]),
        "gastos_por_grupo": gastos_por_grupo,
    }


# FIX: agregado auth en ambos endpoints
@router.get("/resumen/{mes}")
def get_resumen(mes: str, auth: dict = Depends(require_internal_auth)):
    return _resumen_mes(mes)


@router.get("/exportar/{mes}")
def exportar_excel(mes: str, auth: dict = Depends(require_internal_auth)):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    data = _resumen_mes(mes)
    wb   = Workbook()

    # ── Estilos ──
    NAVY      = "0D1B2A"
    BLUE      = "1E40AF"
    GREEN     = "166534"
    RED       = "991B1B"
    YELLOW    = "854D0E"
    BG_GRAY   = "F1F5F9"
    BG_GREEN  = "F0FDF4"
    BG_RED    = "FEF2F2"
    BG_BLUE   = "EFF6FF"
    BG_YELLOW = "FEFCE8"

    def header_font(color=None):
        return Font(name="Arial", bold=True, color=color or "FFFFFF", size=11)

    def cell_font(bold=False, color="0F172A", size=10):
        return Font(name="Arial", bold=bold, color=color, size=size)

    def fill(hex_color):
        return PatternFill("solid", start_color=hex_color, fgColor=hex_color)

    def border():
        thin = Side(style="thin", color="E2E8F0")
        return Border(left=thin, right=thin, top=thin, bottom=thin)

    def center():
        return Alignment(horizontal="center", vertical="center")

    # ======================================================
    # HOJA 1 — RESUMEN EJECUTIVO
    # ======================================================
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:F1")
    ws["A1"] = f"Instituto de Cirugía Articular — Resumen Contable {mes}"
    ws["A1"].font      = Font(name="Arial", bold=True, size=14, color=NAVY)
    ws["A1"].alignment = center()
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:F2")
    ws["A2"] = f"Período: {mes}"
    ws["A2"].font      = Font(name="Arial", size=10, color="64748B")
    ws["A2"].alignment = center()
    ws.row_dimensions[2].height = 18

    kpis = [
        ("Ingresos totales",  data["ingresos_total"],  BG_GREEN,  GREEN),
        ("Anulaciones",      -data["anulados_total"],   BG_RED,    RED),
        ("Gastos totales",   -data["gastos_total"],     BG_YELLOW, YELLOW),
        ("Utilidad neta",     data["utilidad_neta"],    BG_BLUE,   BLUE),
    ]

    ws.row_dimensions[4].height = 14
    ws.row_dimensions[5].height = 20
    ws.row_dimensions[6].height = 36
    ws.row_dimensions[7].height = 20

    for i, (label, valor, bg, color) in enumerate(kpis):
        col = i + 1
        ws.cell(row=5, column=col, value=label).font      = Font(name="Arial", size=9, bold=True, color="64748B")
        ws.cell(row=5, column=col).alignment = Alignment(horizontal="center")
        ws.cell(row=5, column=col).fill      = fill(bg)
        ws.cell(row=5, column=col).border    = border()
        cell = ws.cell(row=6, column=col, value=valor)
        cell.font          = Font(name="Arial", size=16, bold=True, color=color)
        cell.alignment     = center()
        cell.fill          = fill(bg)
        cell.number_format = "$#,##0;($#,##0);\"-\""
        cell.border        = border()

    ws["A9"] = "Gastos por grupo"
    ws["A9"].font = Font(name="Arial", bold=True, size=11, color=NAVY)
    ws.row_dimensions[9].height = 22

    for j, h in enumerate(["Grupo", "Total ($)"]):
        cell = ws.cell(row=10, column=j+1, value=h)
        cell.font      = header_font()
        cell.fill      = fill(NAVY)
        cell.alignment = center()
        cell.border    = border()

    row = 11
    for grupo, total in data["gastos_por_grupo"].items():
        ws.cell(row=row, column=1, value=grupo).font   = cell_font()
        ws.cell(row=row, column=1).border = border()
        ws.cell(row=row, column=1).fill   = fill(BG_GRAY)
        mc = ws.cell(row=row, column=2, value=-total)
        mc.font          = cell_font(bold=True, color=RED)
        mc.number_format = "$#,##0;($#,##0);\"-\""
        mc.border        = border()
        mc.fill          = fill(BG_GRAY)
        row += 1

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18

    # ======================================================
    # HOJA 2 — INGRESOS
    # ======================================================
    ws2 = wb.create_sheet("Ingresos")
    ws2.sheet_view.showGridLines = False

    ws2.merge_cells("A1:G1")
    ws2["A1"] = f"Ingresos — {mes}"
    ws2["A1"].font      = Font(name="Arial", bold=True, size=13, color=NAVY)
    ws2["A1"].alignment = center()
    ws2.row_dimensions[1].height = 28

    for j, h in enumerate(["Fecha", "Hora", "RUT", "Tipo atención", "Profesional", "Método", "Monto ($)"]):
        cell = ws2.cell(row=2, column=j+1, value=h)
        cell.font      = header_font()
        cell.fill      = fill(BLUE)
        cell.alignment = center()
        cell.border    = border()
    ws2.row_dimensions[2].height = 20

    for i, ing in enumerate(data["ingresos"]):
        row = i + 3
        bg = "FFFFFF" if i % 2 == 0 else BG_GRAY
        for j, v in enumerate([ing["fecha"], ing["time"], ing["rut"], ing["tipo"],
                                ing["professional"], ing["metodo"], ing["monto"]]):
            c = ws2.cell(row=row, column=j+1, value=v)
            c.font   = cell_font()
            c.fill   = fill(bg)
            c.border = border()
            if j == 6:
                c.number_format = "$#,##0;($#,##0);\"-\""
                c.font = cell_font(bold=True, color=GREEN)

    total_row = len(data["ingresos"]) + 3
    ws2.cell(row=total_row, column=6, value="TOTAL").font   = header_font(NAVY)
    ws2.cell(row=total_row, column=6).fill   = fill(BG_GREEN)
    ws2.cell(row=total_row, column=6).border = border()
    tc = ws2.cell(row=total_row, column=7, value=data["ingresos_total"])
    tc.font          = Font(name="Arial", bold=True, size=11, color=GREEN)
    tc.number_format = "$#,##0;($#,##0);\"-\""
    tc.fill          = fill(BG_GREEN)
    tc.border        = border()

    for col, w in zip("ABCDEFG", [12, 8, 14, 20, 16, 14, 14]):
        ws2.column_dimensions[col].width = w

    # ======================================================
    # HOJA 3 — ANULACIONES
    # ======================================================
    ws3 = wb.create_sheet("Anulaciones")
    ws3.sheet_view.showGridLines = False

    ws3.merge_cells("A1:G1")
    ws3["A1"] = f"Anulaciones — {mes}"
    ws3["A1"].font      = Font(name="Arial", bold=True, size=13, color=NAVY)
    ws3["A1"].alignment = center()
    ws3.row_dimensions[1].height = 28

    for j, h in enumerate(["Fecha", "Hora", "RUT", "Tipo atención", "Profesional", "Motivo", "Monto ($)"]):
        cell = ws3.cell(row=2, column=j+1, value=h)
        cell.font      = header_font()
        cell.fill      = fill("7F1D1D")
        cell.alignment = center()
        cell.border    = border()

    for i, anu in enumerate(data["anulados"]):
        row = i + 3
        bg = "FFFFFF" if i % 2 == 0 else BG_RED
        for j, v in enumerate([anu["fecha"], anu["time"], anu["rut"], anu["tipo"],
                                anu["professional"], anu["motivo"], anu["monto"]]):
            c = ws3.cell(row=row, column=j+1, value=v)
            c.font   = cell_font()
            c.fill   = fill(bg)
            c.border = border()
            if j == 6:
                c.number_format = "$#,##0;($#,##0);\"-\""
                c.font = cell_font(bold=True, color=RED)

    total_row3 = len(data["anulados"]) + 3
    ws3.cell(row=total_row3, column=6, value="TOTAL").font   = header_font(NAVY)
    ws3.cell(row=total_row3, column=6).fill   = fill(BG_RED)
    ws3.cell(row=total_row3, column=6).border = border()
    tc3 = ws3.cell(row=total_row3, column=7, value=-data["anulados_total"])
    tc3.font          = Font(name="Arial", bold=True, size=11, color=RED)
    tc3.number_format = "$#,##0;($#,##0);\"-\""
    tc3.fill          = fill(BG_RED)
    tc3.border        = border()

    for col, w in zip("ABCDEFG", [12, 8, 14, 20, 16, 20, 14]):
        ws3.column_dimensions[col].width = w

    # ======================================================
    # HOJA 4 — GASTOS
    # ======================================================
    ws4 = wb.create_sheet("Gastos")
    ws4.sheet_view.showGridLines = False

    ws4.merge_cells("A1:F1")
    ws4["A1"] = f"Gastos — {mes}"
    ws4["A1"].font      = Font(name="Arial", bold=True, size=13, color=NAVY)
    ws4["A1"].alignment = center()
    ws4.row_dimensions[1].height = 28

    for j, h in enumerate(["Grupo", "Categoría", "Descripción", "Fecha ingreso", "Monto ($)"]):
        cell = ws4.cell(row=2, column=j+1, value=h)
        cell.font      = header_font()
        cell.fill      = fill(YELLOW)
        cell.alignment = center()
        cell.border    = border()

    for i, gas in enumerate(data["gastos"]):
        row = i + 3
        bg = "FFFFFF" if i % 2 == 0 else BG_YELLOW
        for j, v in enumerate([gas["grupo"], gas["categoria"], gas["descripcion"],
                                gas["created_at"][:10] if gas["created_at"] else "", gas["monto"]]):
            c = ws4.cell(row=row, column=j+1, value=v)
            c.font   = cell_font()
            c.fill   = fill(bg)
            c.border = border()
            if j == 4:
                c.number_format = "$#,##0;($#,##0);\"-\""
                c.font = cell_font(bold=True, color=YELLOW)

    total_row4 = len(data["gastos"]) + 3
    ws4.cell(row=total_row4, column=4, value="TOTAL").font   = header_font(NAVY)
    ws4.cell(row=total_row4, column=4).fill   = fill(BG_YELLOW)
    ws4.cell(row=total_row4, column=4).border = border()
    tc4 = ws4.cell(row=total_row4, column=5, value=-data["gastos_total"])
    tc4.font          = Font(name="Arial", bold=True, size=11, color=YELLOW)
    tc4.number_format = "$#,##0;($#,##0);\"-\""
    tc4.fill          = fill(BG_YELLOW)
    tc4.border        = border()

    for col, w in zip("ABCDE", [20, 20, 30, 14, 14]):
        ws4.column_dimensions[col].width = w

    # ======================================================
    # GUARDAR Y DEVOLVER
    # ======================================================
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=contable_{mes}.xlsx"}
    )

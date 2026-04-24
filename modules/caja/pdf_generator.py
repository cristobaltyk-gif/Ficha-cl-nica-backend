# ============================================================
# pdf_generator.py
# Genera el PDF mensual de caja con ReportLab.
# Llamado desde caja_router.py — sin lógica de negocio aquí.
# ============================================================

import io
from pathlib import Path

def generar_pdf_mes(data: dict, month: str, professional: str = None) -> io.BytesIO:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise RuntimeError("reportlab no instalado")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    title_style   = ParagraphStyle("title",   parent=styles["Heading1"], fontSize=16, spaceAfter=4,  alignment=TA_CENTER)
    sub_style     = ParagraphStyle("sub",     parent=styles["Normal"],   fontSize=10, spaceAfter=12, alignment=TA_CENTER, textColor=colors.grey)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=6)

    def fmt(monto):
        return f"${monto:,}".replace(",", ".")

    subtitle = f"Resumen contable — {month}"
    if professional:
        subtitle += f" — {professional}"

    story.append(Paragraph("Instituto de Cirugía Articular", title_style))
    story.append(Paragraph(subtitle, sub_style))
    story.append(Spacer(1, 0.3*cm))

    # KPIs
    kpi_data = [
        ["Total recaudado", "Retención", "Neto", "Total pagos", "Anulados"],
        [
            fmt(data["monto_total"]),
            fmt(data["retencion_total"]),
            fmt(data["neto_total"]),
            str(data["total_pagos"]),
            str(data["total_anulados"]),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3*cm, 3*cm])
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

    # Por profesional — solo admin/secretaria (professional=None)
    if not professional:
        story.append(Paragraph("Por profesional", section_style))
        prof_data = [["Profesional", "Pagos", "Bruto", "Retención", "Neto"]]
        for prof, vals in data["por_profesional"].items():
            prof_data.append([
                prof,
                str(vals["pagos"]),
                fmt(vals["monto"]),
                fmt(vals["retencion"]),
                fmt(vals["neto"]),
            ])
        prof_table = Table(prof_data, colWidths=[5*cm, 2.5*cm, 3.5*cm, 3.5*cm, 3*cm])
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
        tipo_data.append([tipo, str(vals["count"]), fmt(vals["monto"])])
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
        met_data.append([met.capitalize(), str(vals["count"]), fmt(vals["monto"])])
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
            fmt(p["monto"]),
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
    return buf

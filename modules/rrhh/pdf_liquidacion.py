"""
modules/rrhh/pdf_liquidacion.py
Genera PDF de liquidación de sueldo — dos columnas haberes/descuentos + firma.
"""

from __future__ import annotations

import io


def generar_pdf(liq: dict, buffer: io.BytesIO) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=1.8*cm, rightMargin=1.8*cm,
                               topMargin=1.8*cm,  bottomMargin=1.8*cm)
    styles = getSampleStyleSheet()
    story  = []

    NAVY  = colors.HexColor("#0D1B2A")
    GRAY  = colors.HexColor("#F1F5F9")
    GREEN = colors.HexColor("#166534")
    RED   = colors.HexColor("#991B1B")
    BLUE  = colors.HexColor("#1E40AF")
    LINE  = colors.HexColor("#E2E8F0")

    def clp(n):
        return f"${abs(int(n)):,}".replace(",", ".")

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    title_s = ps("t",   fontSize=15, fontName="Helvetica-Bold",
                        textColor=colors.white, alignment=TA_CENTER)
    sub_s   = ps("s",   fontSize=9,  textColor=colors.HexColor("#94A3B8"),
                        alignment=TA_CENTER, spaceAfter=10)
    hdr_s   = ps("h",   fontSize=8,  fontName="Helvetica-Bold",
                        textColor=colors.HexColor("#64748B"))
    item_s  = ps("i",   fontSize=9,  textColor=colors.HexColor("#374151"))
    amt_s   = ps("a",   fontSize=9,  alignment=TA_RIGHT,
                        textColor=colors.HexColor("#0F172A"))
    red_s   = ps("r",   fontSize=9,  alignment=TA_RIGHT, textColor=RED)
    green_s = ps("g",   fontSize=9,  alignment=TA_RIGHT, textColor=GREEN)
    bold_g  = ps("bg",  fontSize=10, fontName="Helvetica-Bold",
                        alignment=TA_RIGHT, textColor=GREEN)
    total_s = ps("tot", fontSize=10, fontName="Helvetica-Bold",
                        textColor=colors.HexColor("#0F172A"))
    firm_s  = ps("f",   fontSize=8,  textColor=colors.HexColor("#64748B"),
                        alignment=TA_CENTER)

    # ── HEADER ──
    hdr = Table([[Paragraph("LIQUIDACIÓN DE SUELDO", title_s)]], colWidths=[17.4*cm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(f"Instituto de Cirugía Articular · {liq['mes']}", sub_s))

    # ── DATOS TRABAJADOR ──
    info_rows = [
        ["Trabajador", liq["nombre"],       "RUT",      liq.get("rut","")],
        ["Cargo",      liq.get("cargo",""), "Contrato", liq["tipo_contrato"].replace("_"," ").capitalize()],
    ]
    if not liq.get("es_honorarios"):
        info_rows.append(["AFP", liq.get("afp",""), "Salud", liq.get("salud","")])

    il = ps("il",  fontSize=8, textColor=colors.HexColor("#64748B"))
    iv = ps("iv",  fontSize=9, textColor=NAVY)

    info_data = [
        [Paragraph(f"<b>{r[0]}</b>", il), Paragraph(r[1], iv),
         Paragraph(f"<b>{r[2]}</b>", il), Paragraph(r[3], iv)]
        for r in info_rows
    ]
    info_t = Table(info_data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.9*cm])
    info_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [colors.white, GRAY]),
        ("GRID",           (0,0),(-1,-1), 0.5, LINE),
        ("TOPPADDING",     (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 5),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 0.4*cm))

    # ── HONORARIOS — tabla simple ──
    if liq.get("es_honorarios"):
        rows = [
            [Paragraph("Monto bruto boleta", item_s), Paragraph(clp(liq["sueldo_base"]),      amt_s)],
            [Paragraph("Retención 10.75%",   item_s), Paragraph(f"({clp(liq['retencion_boleta'])})", red_s)],
        ]
        t = Table(rows, colWidths=[12*cm, 5.4*cm])
        t.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0,0),(-1,-1), [colors.white, GRAY]),
            ("GRID",           (0,0),(-1,-1), 0.5, LINE),
            ("TOPPADDING",     (0,0),(-1,-1), 6),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 6),
            ("LEFTPADDING",    (0,0),(-1,-1), 10),
            ("RIGHTPADDING",   (0,0),(-1,-1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*cm))
        liq_r = Table(
            [[Paragraph("LÍQUIDO A PAGAR", total_s), Paragraph(clp(liq["liquido"]), bold_g)]],
            colWidths=[12*cm, 5.4*cm]
        )
        liq_r.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F0FDF4")),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        story.append(liq_r)

    # ── CONTRATO NORMAL — DOS COLUMNAS ──
    else:
        # Columna izquierda: HABERES
        haberes = [
            [Paragraph("HABERES", hdr_s), Paragraph("", amt_s)],
            [Paragraph("Sueldo base", item_s), Paragraph(clp(liq["sueldo_base"]), amt_s)],
        ]
        for b in liq.get("bonos", []):
            if b.get("monto", 0) > 0:
                haberes.append([
                    Paragraph(b["nombre"], item_s),
                    Paragraph(clp(b["monto"]), green_s)
                ])
        total_h = liq["sueldo_base"] + liq["total_bonos"]
        haberes.append([
            Paragraph("<b>Total haberes</b>", ps("tbh", fontSize=9, fontName="Helvetica-Bold")),
            Paragraph(f"<b>{clp(total_h)}</b>",
                      ps("tba", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT))
        ])

        # Columna derecha: DESCUENTOS
        descuentos = [
            [Paragraph("DESCUENTOS", hdr_s), Paragraph("", red_s)],
            [Paragraph(f"AFP {liq.get('afp','')}", item_s),
             Paragraph(f"({clp(liq['descuento_afp'])})", red_s)],
            [Paragraph("Salud", item_s),
             Paragraph(f"({clp(liq['descuento_salud'])})", red_s)],
            [Paragraph("AFC trabajador", item_s),
             Paragraph(f"({clp(liq['descuento_afc'])})", red_s)],
            [Paragraph("Impuesto único 2ª cat.", item_s),
             Paragraph(f"({clp(liq['impuesto_unico'])})", red_s)],
            [
                Paragraph("<b>Total descuentos</b>",
                          ps("tdd", fontSize=9, fontName="Helvetica-Bold")),
                Paragraph(f"<b>({clp(liq['total_descuentos'])})</b>",
                          ps("tdr", fontSize=9, fontName="Helvetica-Bold",
                             alignment=TA_RIGHT, textColor=RED))
            ],
        ]

        def mk_col(rows, hdr_bg):
            t = Table(rows, colWidths=[5.2*cm, 3*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0),  hdr_bg),
                ("ROWBACKGROUNDS",(0,1), (-1,-2), [colors.white, GRAY]),
                ("BACKGROUND",    (0,-1),(-1,-1), GRAY),
                ("GRID",          (0,0), (-1,-1), 0.5, LINE),
                ("TOPPADDING",    (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ]))
            return t

        two_col = Table([[
            mk_col(haberes,    colors.HexColor("#EFF6FF")),
            mk_col(descuentos, colors.HexColor("#FEF2F2")),
        ]], colWidths=[8.4*cm, 9*cm])
        two_col.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ]))
        story.append(two_col)
        story.append(Spacer(1, 0.3*cm))

        # LÍQUIDO
        liq_r = Table([[
            Paragraph("SUELDO LÍQUIDO A PAGAR", total_s),
            Paragraph(clp(liq["liquido"]), bold_g),
        ]], colWidths=[12*cm, 5.4*cm])
        liq_r.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F0FDF4")),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("LINEBELOW",     (0,0),(-1,-1), 1.5, GREEN),
        ]))
        story.append(liq_r)
        story.append(Spacer(1, 0.15*cm))

        # Costo empresa — línea pequeña
        costo_t = Table([[
            Paragraph(
                f"Costo empresa: <b>{clp(liq['costo_empresa'])}</b>  "
                f"<font color='#94A3B8' size=7.5>"
                f"SIS {clp(liq['costo_sis'])}  "
                f"Mutual {clp(liq['costo_mutual'])}  "
                f"AFC emp. {clp(liq['costo_afc_empleador'])}</font>",
                ps("ce", fontSize=8, textColor=BLUE)
            ),
        ]], colWidths=[17.4*cm])
        costo_t.setStyle(TableStyle([
            ("LEFTPADDING",  (0,0),(-1,-1), 12),
            ("TOPPADDING",   (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story.append(costo_t)

    # ── FIRMA ──
    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story.append(Spacer(1, 0.8*cm))

    def firma_col(nombre, titulo):
        return Table([
            [Paragraph("", firm_s)],
            [HRFlowable(width=6*cm, thickness=0.5, color=NAVY)],
            [Paragraph(nombre, ps("fn", fontSize=9, fontName="Helvetica-Bold",
                                  textColor=NAVY, alignment=TA_CENTER))],
            [Paragraph(titulo,  ps("ft", fontSize=8, textColor=colors.HexColor("#94A3B8"),
                                   alignment=TA_CENTER))],
        ], colWidths=[7*cm])

    firma = Table([[
        firma_col(liq["nombre"], f"Firma trabajador · RUT {liq.get('rut','')}"),
        firma_col("Instituto de Cirugía Articular", "Empleador"),
    ]], colWidths=[8.7*cm, 8.7*cm])
    firma.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "BOTTOM"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(firma)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Instituto de Cirugía Articular · Curicó, Chile · {liq['mes']}",
        ps("foot", fontSize=7.5, textColor=colors.HexColor("#CBD5E1"), alignment=TA_CENTER)
    ))

    doc.build(story)
  

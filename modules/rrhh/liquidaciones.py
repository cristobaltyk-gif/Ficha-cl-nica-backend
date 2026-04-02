"""
modules/rrhh/liquidaciones.py
Endpoints de liquidaciones — cálculo, PDF, Excel, registrar gasto contable.
"""

from __future__ import annotations

import io
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from modules.rrhh.tasas        import load_tasas
from modules.rrhh.trabajadores import load_trabajadores, calcular_liquidacion

router = APIRouter(prefix="/api/rrhh", tags=["RRHH - Liquidaciones"])


# ======================================================
# HELPERS
# ======================================================

def calcular_resumen_mes(mes: str) -> dict:
    trabajadores = load_trabajadores()
    tasas        = load_tasas()
    activos      = [t for t in trabajadores.values() if t.get("activo", True)]
    liqds        = [calcular_liquidacion(t, tasas, mes) for t in activos]
    return {
        "mes":                 mes,
        "trabajadores":        len(liqds),
        "liquidaciones":       liqds,
        "total_liquidos":      sum(l["liquido"] for l in liqds),
        "total_descuentos":    sum(l.get("total_descuentos", l.get("retencion_boleta", 0)) for l in liqds),
        "total_costo_empresa": sum(l["costo_empresa"] for l in liqds),
    }


# ======================================================
# ENDPOINTS
# ======================================================

@router.get("/liquidacion/{tid}/{mes}")
def get_liquidacion(tid: str, mes: str):
    trabajadores = load_trabajadores()
    if tid not in trabajadores:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    return calcular_liquidacion(trabajadores[tid], load_tasas(), mes)


@router.get("/liquidaciones/{mes}")
def get_liquidaciones_mes(mes: str):
    return calcular_resumen_mes(mes)


@router.post("/liquidaciones/{mes}/registrar-gasto")
def registrar_gasto_sueldos(mes: str):
    data = calcular_resumen_mes(mes)
    try:
        import httpx
        httpx.post(
            f"{os.getenv('BACKEND_URL','http://localhost:10000')}/api/contable/gastos",
            json={
                "mes":         mes,
                "grupo":       "fijos",
                "categoria":   "Sueldos",
                "descripcion": f"Remuneraciones {mes} — {data['trabajadores']} trabajadores",
                "monto":       data["total_costo_empresa"],
            },
            timeout=10
        )
    except:
        pass
    return {"ok": True, "monto": data["total_costo_empresa"]}


@router.get("/liquidacion/{tid}/{mes}/pdf")
def pdf_liquidacion(tid: str, mes: str):
    from modules.rrhh.pdf_liquidacion import generar_pdf
    trabajadores = load_trabajadores()
    if tid not in trabajadores:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    liq = calcular_liquidacion(trabajadores[tid], load_tasas(), mes)
    buf = io.BytesIO()
    generar_pdf(liq, buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=liquidacion_{tid}_{mes}.pdf"})


@router.get("/liquidaciones/{mes}/excel")
def excel_liquidaciones(mes: str):
    from modules.rrhh.excel_liquidacion import generar_excel
    data = calcular_resumen_mes(mes)
    buf  = io.BytesIO()
    generar_excel(data, buf)
    buf.seek(0)
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=remuneraciones_{mes}.xlsx"})
            

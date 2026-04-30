"""
modules/caja/caja_router.py
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from collections import defaultdict

from modules.caja.caja_config_helper import get_tipos_profesional, get_valor_tipo
from auth.internal_auth import require_internal_auth
from modules.caja.comisiones_store import calcular as calcular_comision
from db.supabase_client import (
    get_caja_slot, get_caja_day, save_caja_slot, delete_caja_slot,
    get_pagos_day, get_pagos_mes, save_pago, update_pago
)
from agenda.store import read_day as read_agenda_day

router = APIRouter(prefix="/api/caja", tags=["Caja"])

TIPOS_VALIDOS   = {"particular","control_costo","control_gratuito","sobrecupo","kinesiologia","paquete_10"}
TIPOS_GRATUITOS = {"control_gratuito"}
ESTADOS_VALIDOS = {"waiting","paid"}
METODOS_VALIDOS = {"efectivo","transferencia","tarjeta"}
TIPOS_LABELS    = {
    "particular":"Particular","control_costo":"Control con costo",
    "control_gratuito":"Control gratuito","sobrecupo":"Sobrecupo",
    "kinesiologia":"Kinesiología","paquete_10":"Paquete 10 sesiones",
}
ROLES_ADMIN = {"admin","secretaria"}


def _can_see_all(auth):    return auth["role"]["name"] in ROLES_ADMIN
def _resolve_professional(auth, requested=None): return requested if _can_see_all(auth) else auth["professional"]


def _load_agenda_day(date, professional):
    day_data = read_agenda_day(date)
    return day_data.get(professional, {}).get("slots", {})


def _load_agenda_professionals(date):
    from core.professionals_store import list_professionals
    valid_ids = {p["id"] for p in list_professionals()}
    day_data  = read_agenda_day(date)
    return [k for k in day_data.keys() if k in valid_ids]


class CajaUpdate(BaseModel):
    date: str; professional: str; time: str
    arrival_status: Optional[str] = None
    tipo_atencion:  Optional[str] = None
    pagado:         Optional[bool] = None
    hora_llegada:   Optional[str] = None

class CajaSlotDelete(BaseModel):
    date: str; professional: str; time: str

class PagoCreate(BaseModel):
    date: str; professional: str; time: str; rut: str; tipo_atencion: str
    metodo_pago:      Optional[str] = None
    numero_operacion: Optional[str] = None
    banco_origen:     Optional[str] = None
    pagado_por:       Optional[str] = None

class AnulacionCreate(BaseModel):
    date: str; professional: str; time: str; motivo: str
    anulado_por: Optional[str] = None


@router.get("/config")
def get_config(professional: Optional[str] = Query(None)):
    if professional:
        return get_tipos_profesional(professional)
    from db.supabase_client import get_caja_config
    config = get_caja_config()
    return {k: v for k, v in config.items() if k != "por_profesional"}


@router.get("/day")
def get_caja_day_endpoint(date: str, professional: str, auth=Depends(require_internal_auth)):
    professional = _resolve_professional(auth, professional)
    agenda_slots = _load_agenda_day(date, professional)
    caja         = get_caja_day(date, professional)
    result = []
    for time, slot in agenda_slots.items():
        if slot.get("status") not in ("reserved","confirmed"):
            continue
        cs    = caja.get(time, {})
        tipo  = cs.get("tipo_atencion","particular")
        monto = get_valor_tipo(professional, tipo)
        result.append({
            "time": time, "rut": slot.get("rut",""),
            "arrival_status": cs.get("arrival_status"),
            "tipo_atencion": tipo, "monto": monto,
            "pagado": cs.get("pagado", False),
            "es_gratuito": tipo in TIPOS_GRATUITOS,
            "hora_llegada": cs.get("hora_llegada"),
        })
    result.sort(key=lambda x: x["time"])
    return {"date": date, "professional": professional, "slots": result}


@router.patch("/slot")
def update_caja_slot(data: CajaUpdate, auth=Depends(require_internal_auth)):
    if data.arrival_status and data.arrival_status not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="arrival_status inválido")
    if data.tipo_atencion and data.tipo_atencion not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="tipo_atencion inválido")
    professional = _resolve_professional(auth, data.professional)
    cs = get_caja_slot(data.date, professional, data.time)
    if data.arrival_status is not None: cs["arrival_status"] = data.arrival_status
    if data.tipo_atencion is not None:
        cs["tipo_atencion"] = data.tipo_atencion
        cs["monto"]         = get_valor_tipo(professional, data.tipo_atencion)
        cs["es_gratuito"]   = data.tipo_atencion in TIPOS_GRATUITOS
    if data.pagado is not None: cs["pagado"] = data.pagado
    if data.hora_llegada is not None: cs["hora_llegada"] = data.hora_llegada
    save_caja_slot(data.date, professional, data.time, cs)
    return {"ok": True, "time": data.time}


@router.delete("/slot")
def delete_caja_slot_endpoint(data: CajaSlotDelete, auth=Depends(require_internal_auth)):
    professional = _resolve_professional(auth, data.professional)
    delete_caja_slot(data.date, professional, data.time)
    return {"ok": True, "time": data.time}


@router.post("/pago")
def registrar_pago(data: PagoCreate, auth=Depends(require_internal_auth)):
    professional = _resolve_professional(auth, data.professional)
    if data.tipo_atencion not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail="tipo_atencion inválido")
    es_gratuito = data.tipo_atencion in TIPOS_GRATUITOS
    if not es_gratuito:
        if not data.metodo_pago or data.metodo_pago not in METODOS_VALIDOS:
            raise HTTPException(status_code=400, detail="metodo_pago inválido")
        if data.metodo_pago in ("transferencia","tarjeta") and not data.numero_operacion:
            raise HTTPException(status_code=400, detail="numero_operacion requerido")
    monto = get_valor_tipo(professional, data.tipo_atencion)
    save_pago(data.date, professional, data.time, {
        "rut": data.rut, "tipo_atencion": data.tipo_atencion, "monto": monto,
        "es_gratuito": es_gratuito,
        "metodo_pago": data.metodo_pago if not es_gratuito else None,
        "numero_operacion": data.numero_operacion, "banco_origen": data.banco_origen,
        "pagado_at": datetime.now().isoformat(timespec="seconds"),
        "pagado_por": data.pagado_por, "anulado": False,
        "anulacion_motivo": None, "anulacion_at": None, "anulado_por": None,
    })
    cs = get_caja_slot(data.date, professional, data.time)
    cs.update({"arrival_status":"paid","pagado":True,"tipo_atencion":data.tipo_atencion,"monto":monto})
    save_caja_slot(data.date, professional, data.time, cs)
    return {"ok": True, "monto": monto, "es_gratuito": es_gratuito}


@router.post("/anular")
def anular_pago(data: AnulacionCreate, auth=Depends(require_internal_auth)):
    professional = _resolve_professional(auth, data.professional)
    pagos = get_pagos_day(data.date, professional)
    if data.time not in pagos:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if pagos[data.time].get("anulado"):
        raise HTTPException(status_code=400, detail="Pago ya anulado")
    update_pago(data.date, professional, data.time, {
        "anulado": True, "anulacion_motivo": data.motivo,
        "anulacion_at": datetime.now().isoformat(timespec="seconds"),
        "anulado_por": data.anulado_por,
    })
    delete_caja_slot(data.date, professional, data.time)
    return {"ok": True}


def _get_caja_summary(date, professional):
    agenda_slots = _load_agenda_day(date, professional)
    caja         = get_caja_day(date, professional)
    pagos        = get_pagos_day(date, professional)
    slots = []
    for time, slot in agenda_slots.items():
        if slot.get("status") not in ("reserved","confirmed"):
            continue
        cs   = caja.get(time, {})
        tipo = cs.get("tipo_atencion","particular")
        slots.append({
            "time": time, "rut": slot.get("rut",""),
            "arrival_status": cs.get("arrival_status"),
            "tipo_atencion": tipo, "monto": get_valor_tipo(professional, tipo),
            "pagado": cs.get("pagado",False), "es_gratuito": tipo in TIPOS_GRATUITOS,
        })
    total_pacientes = len(slots)
    esperando       = sum(1 for s in slots if s["arrival_status"]=="waiting" and not s["pagado"])
    pagados_count   = sum(1 for s in slots if s["pagado"])
    monto_total     = sum(p["monto"] for p in pagos.values() if not p.get("anulado"))
    por_tipo = {}; por_metodo = {}; pacientes = []
    for time, p in pagos.items():
        if p.get("anulado"): continue
        t = p["tipo_atencion"]; m = p.get("metodo_pago") or "gratuito"
        por_tipo[t]   = por_tipo.get(t,0)+1
        por_metodo[m] = por_metodo.get(m,0)+1
        pacientes.append({"time":time,"rut":p.get("rut",""),"tipo_atencion":t,
            "tipo_label":TIPOS_LABELS.get(t,t),"monto":p.get("monto",0),
            "metodo_pago":m,"es_gratuito":p.get("es_gratuito",False),"pagado_at":p.get("pagado_at")})
    pacientes.sort(key=lambda x: x["time"])
    comision = calcular_comision(professional, monto_total)
    return {
        "date":date,"professional":professional,"total_pacientes":total_pacientes,
        "esperando":esperando,"pagados":pagados_count,"monto_total":monto_total,
        "retencion":comision["retencion"],"neto":comision["neto"],
        "porcentaje_comision":comision["porcentaje"],
        "por_tipo":por_tipo,"por_metodo":por_metodo,"pacientes":pacientes,
    }


def _compute_resumen_mes(month, professional=None):
    pagos_list_raw = get_pagos_mes(month)
    if not pagos_list_raw:
        return {"month":month,"monto_total":0,"retencion_total":0,"neto_total":0,
                "total_pagos":0,"total_anulados":0,"por_dia":[],"por_profesional":{},
                "por_tipo":{},"por_metodo":{},"pagos":[]}
    monto_total=0; total_pagos=0; total_anulados=0
    por_dia=defaultdict(int); por_prof=defaultdict(lambda:{"monto":0,"pagos":0,"retencion":0,"neto":0})
    por_tipo=defaultdict(lambda:{"count":0,"monto":0}); por_metodo=defaultdict(lambda:{"count":0,"monto":0})
    pagos_out=[]
    for p in pagos_list_raw:
        prof=p["professional"]
        if professional and prof!=professional: continue
        if p.get("anulado"): total_anulados+=1; continue
        monto=p.get("monto",0); tipo=p.get("tipo_atencion",""); met=p.get("metodo_pago") or "gratuito"
        monto_total+=monto; total_pagos+=1; por_dia[p["fecha"]]+=monto
        por_prof[prof]["monto"]+=monto; por_prof[prof]["pagos"]+=1
        _c=calcular_comision(prof,monto)
        por_prof[prof]["retencion"]+=_c["retencion"]; por_prof[prof]["neto"]+=_c["neto"]
        por_tipo[TIPOS_LABELS.get(tipo,tipo)]["count"]+=1; por_tipo[TIPOS_LABELS.get(tipo,tipo)]["monto"]+=monto
        por_metodo[met]["count"]+=1; por_metodo[met]["monto"]+=monto
        pagos_out.append({"date":p["fecha"],"time":p["time"],"professional":prof,
            "rut":p.get("rut",""),"tipo_atencion":TIPOS_LABELS.get(tipo,tipo),
            "monto":monto,"metodo_pago":met,"es_gratuito":p.get("es_gratuito",False),
            "pagado_at":p.get("pagado_at"),"pagado_por":p.get("pagado_por")})
    pagos_out.sort(key=lambda x:(x["date"],x["time"]))
    return {
        "month":month,"monto_total":monto_total,
        "retencion_total":sum(v["retencion"] for v in por_prof.values()),
        "neto_total":sum(v["neto"] for v in por_prof.values()),
        "total_pagos":total_pagos,"total_anulados":total_anulados,
        "por_dia":[{"date":d,"monto":m} for d,m in sorted(por_dia.items())],
        "por_profesional":dict(por_prof),"por_tipo":dict(por_tipo),
        "por_metodo":dict(por_metodo),"pagos":pagos_out,
    }


@router.get("/summary")
def get_caja_summary(date: str, professional: str, auth=Depends(require_internal_auth)):
    return _get_caja_summary(date, _resolve_professional(auth, professional))


@router.get("/resumen-dia")
def get_resumen_dia(date: str, professional: Optional[str]=Query(None), auth=Depends(require_internal_auth)):
    professional  = _resolve_professional(auth, professional)
    professionals = [professional] if professional else _load_agenda_professionals(date)
    resumen_por_prof=[]; total_global=0; retencion_global=0; neto_global=0
    por_tipo_global={}; por_metodo_global={}; pacientes_global=[]
    for prof in professionals:
        s = _get_caja_summary(date, prof)
        resumen_por_prof.append({"professional":prof,"total_pacientes":s["total_pacientes"],
            "pagados":s["pagados"],"esperando":s["esperando"],"monto_total":s["monto_total"],
            "retencion":s["retencion"],"neto":s["neto"],"porcentaje_comision":s["porcentaje_comision"]})
        total_global+=s["monto_total"]; retencion_global+=s["retencion"]; neto_global+=s["neto"]
        for t,v in s["por_tipo"].items(): por_tipo_global[t]=por_tipo_global.get(t,0)+v
        for m,v in s["por_metodo"].items(): por_metodo_global[m]=por_metodo_global.get(m,0)+v
        for p in s["pacientes"]: pacientes_global.append({**p,"professional":prof})
    pacientes_global.sort(key=lambda x: x["time"])
    return {"date":date,"monto_total":total_global,"retencion_total":retencion_global,
            "neto_total":neto_global,"por_tipo":{TIPOS_LABELS.get(t,t):v for t,v in por_tipo_global.items()},
            "por_metodo":por_metodo_global,"por_profesional":resumen_por_prof,"pacientes":pacientes_global}


@router.get("/resumen-mes")
def get_resumen_mes(month: str, professional: Optional[str]=Query(None), auth=Depends(require_internal_auth)):
    return _compute_resumen_mes(month, _resolve_professional(auth, professional))


@router.get("/pdf-mes")
def get_pdf_mes(month: str, professional: Optional[str]=Query(None), auth=Depends(require_internal_auth)):
    from modules.caja.pdf_generator import generar_pdf_mes
    professional = _resolve_professional(auth, professional)
    data = _compute_resumen_mes(month, professional)
    try:
        buf = generar_pdf_mes(data, month, professional)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    filename = f"caja_{month}_{professional}.pdf" if professional else f"caja_{month}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"})
                

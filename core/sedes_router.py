"""
core/sedes_router.py
--------------------
Reemplaza lectura/escritura de /data/sedes.json → PostgreSQL
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.supabase_client import _get_conn, _utc_now

REGIONES_PATH = Path("/data/regiones.geo.json")

router = APIRouter(
    prefix="/geo/sedes",
    tags=["Sedes"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class CentroModel(BaseModel):
    centro:    str = ""
    direccion: str = ""

class SedesProfesionalModel(BaseModel):
    regiones: Dict[str, List[CentroModel]] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_regiones() -> list:
    try:
        if not REGIONES_PATH.exists():
            return []
        return json.loads(REGIONES_PATH.read_text(encoding="utf-8")).get("regiones", [])
    except Exception:
        return []


def _get_sedes(pid: str) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT regiones FROM sedes WHERE id = %s", (pid,))
            row = cur.fetchone()
            return {"regiones": row["regiones"]} if row else {"regiones": {}}


def _save_sedes(pid: str, regiones: dict) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sedes (id, regiones, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    regiones = EXCLUDED.regiones
            """, (pid, json.dumps(regiones), _utc_now()))
            conn.commit()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/regiones")
def get_regiones():
    regiones = _load_regiones()
    return [{"id": r["id"], "nombre": r["nombre"]} for r in regiones]


@router.get("/{pid}")
def get_sedes_profesional(pid: str):
    return _get_sedes(pid)


@router.put("/{pid}")
def update_sedes_profesional(pid: str, data: SedesProfesionalModel):
    regiones = {k: [c.dict() for c in v] for k, v in data.regiones.items()}
    _save_sedes(pid, regiones)
    return {"ok": True, "pid": pid}


@router.delete("/{pid}")
def delete_sedes_profesional(pid: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sedes WHERE id = %s", (pid,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Profesional no tiene sedes")
            conn.commit()
    return {"ok": True, "pid": pid}
    

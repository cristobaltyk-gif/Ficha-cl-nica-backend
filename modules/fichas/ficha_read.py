from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Depends
from auth.internal_auth import require_internal_auth

BASE_DATA_PATH = Path("data/pacientes")

router = APIRouter(
    prefix="/api/fichas/admin",
    tags=["Ficha Administrativa - Read"],
    dependencies=[Depends(require_internal_auth)]
)

def admin_file(rut: str) -> Path:
    return BASE_DATA_PATH / rut / "admin.json"

@router.get("/{rut}")
def get_ficha_administrativa(rut: str) -> Dict[str, Any]:
    file = admin_file(rut)
    if not file.exists():
        raise HTTPException(404, "Ficha no encontrada")

    return json.loads(file.read_text(encoding="utf-8"))

@router.get("/search")
def search_fichas(q: str = Query(..., min_length=2)):
    results: List[Dict[str, Any]] = []
    q = q.lower()

    if not BASE_DATA_PATH.exists():
        return {"total": 0, "results": []}

    for pdir in BASE_DATA_PATH.iterdir():
        file = pdir / "admin.json"
        if not file.exists():
            continue

        data = json.loads(file.read_text(encoding="utf-8"))
        haystack = " ".join([
            data.get("rut", ""),
            data.get("nombre", ""),
            data.get("apellido_paterno", ""),
            data.get("apellido_materno", "")
        ]).lower()

        if q in haystack:
            results.append(data)

    return {"total": len(results), "results": results}

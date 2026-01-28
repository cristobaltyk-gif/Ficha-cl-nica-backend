from fastapi import APIRouter, HTTPException
from core.professionals_store import (
    list_professionals,
    add_professional,
    update_professional,
    delete_professional,
)

router = APIRouter(prefix="/professionals", tags=["professionals"])


# ==========================
# GET (ya lo tenías)
# ==========================
@router.get("")
def get_all():
    return list_professionals()


# ==========================
# POST (admin agrega)
# ==========================
@router.post("")
def create(professional: dict):
    try:
        return add_professional(professional)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================
# PUT (admin edita)
# ==========================
@router.put("/{pid}")
def update(pid: str, updates: dict):
    try:
        return update_professional(pid, updates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================
# DELETE (admin borra)
# ==========================
@router.delete("/{pid}")
def remove(pid: str):
    try:
        return delete_professional(pid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

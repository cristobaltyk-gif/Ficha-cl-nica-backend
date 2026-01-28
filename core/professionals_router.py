from fastapi import APIRouter, HTTPException
from core.professionals_store import get_active_professionals

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.get("", summary="Lista global de profesionales")
def list_professionals():
    """
    GET /professionals
    """
    try:
        return get_active_professionals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

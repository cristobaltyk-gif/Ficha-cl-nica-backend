from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from agenda import professionals_store as store

router = APIRouter(
    prefix="/admin/professionals",
    tags=["professionals-admin"]
)

# ======================================================
# SCHEMAS
# ======================================================

class Block(BaseModel):
    start: str  # HH:MM
    end: str    # HH:MM


class SetDayRequest(BaseModel):
    weekday: str        # monday, tuesday...
    blocks: List[Block]
    slotMinutes: int = 15


class BlockDateRequest(BaseModel):
    date: str  # YYYY-MM-DD


# ======================================================
# ENDPOINTS
# ======================================================

@router.post("/{professional_id}/day")
def set_day_schedule(professional_id: str, data: SetDayRequest):
    try:
        store.set_day_blocks(
            professional_id=professional_id,
            weekday=data.weekday,
            blocks=[b.dict() for b in data.blocks],
            slot_minutes=data.slotMinutes
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{professional_id}/day/{weekday}")
def close_day(professional_id: str, weekday: str):
    try:
        store.close_day(
            professional_id=professional_id,
            weekday=weekday
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{professional_id}/block-date")
def block_date(professional_id: str, data: BlockDateRequest):
    try:
        store.block_date(
            professional_id=professional_id,
            date_iso=data.date
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{professional_id}/block-date/{date}")
def unblock_date(professional_id: str, date: str):
    try:
        store.unblock_date(
            professional_id=professional_id,
            date_iso=date
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict


SlotStatus = Literal[
    "available",
    "reserved",
    "confirmed",
    "blocked",
    "cancelled",
]


class OccupancyResponse(BaseModel):
    date: str
    time: str
    professionals: Dict[str, SlotStatus] = Field(default_factory=dict)


class CreateSlotRequest(BaseModel):
    date: str
    time: str
    professional: str
    rut: str
    by: str = "secretaria"
    status: SlotStatus = "reserved"
    tipo: str = "presencial"


class ConfirmSlotRequest(BaseModel):
    date: str
    time: str
    professional: str
    by: str = "secretaria"


class CancelSlotRequest(BaseModel):
    date: str
    time: str
    professional: str
    by: str = "secretaria"


class SlotRef(BaseModel):
    date: str
    time: str
    professional: str


class SlotTarget(BaseModel):
    date: str
    time: str


class RescheduleRequest(BaseModel):
    from_slot: SlotRef    = Field(..., alias="from")
    to_slot:   SlotTarget = Field(..., alias="to")
    by: str = "secretaria"


class MutationResult(BaseModel):
    ok: bool
    message: str
    date: str
    professional: str
    slot: Dict[str, object] = Field(default_factory=dict)
    moved_from: Optional[Dict[str, str]] = None
    moved_to:   Optional[Dict[str, str]] = None

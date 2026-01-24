from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict


# -----------------------------
# Estados canónicos de agenda
# -----------------------------
SlotStatus = Literal[
    "available",
    "reserved",
    "confirmed",
    "blocked",
    "cancelled",
]


# -----------------------------
# Lectura de ocupación (respuesta)
# -----------------------------
class OccupancyResponse(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    professionals: Dict[str, SlotStatus] = Field(default_factory=dict)


# -----------------------------
# Crear / Reservar
# -----------------------------
class CreateSlotRequest(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    professional: str
    rut: str
    by: str = "secretaria"
    status: SlotStatus = "reserved"  # por defecto reserva


# -----------------------------
# Anular (volver a available)
# -----------------------------
class CancelSlotRequest(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    professional: str
    by: str = "secretaria"


# -----------------------------
# Cambiar hora (reschedule)
# -----------------------------
class SlotRef(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    professional: str


class SlotTarget(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM


class RescheduleRequest(BaseModel):
    from_slot: SlotRef = Field(..., alias="from")
    to_slot: SlotTarget = Field(..., alias="to")
    by: str = "secretaria"


# -----------------------------
# Respuesta estándar de mutación
# -----------------------------
class MutationResult(BaseModel):
    ok: bool
    message: str
    date: str
    professional: str
    slot: Dict[str, object] = Field(default_factory=dict)  # status, rut?, etc.
    moved_from: Optional[Dict[str, str]] = None
    moved_to: Optional[Dict[str, str]] = None

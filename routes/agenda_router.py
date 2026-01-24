from fastapi import APIRouter, Query
from services.agenda_service import build_agenda

agenda_router = APIRouter()

@agenda_router.get("/agenda")
def get_agenda(date: str = Query(...)):
    return build_agenda(date)

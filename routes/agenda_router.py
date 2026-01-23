from fastapi import APIRouter, Query
from auth.professionals_store import load_professionals

agenda_router = APIRouter()

@agenda_router.get("/agenda")
def get_agenda(date: str = Query(...)):
    professionals_dict = load_professionals()

    professionals = [
        p for p in professionals_dict.values()
        if p.get("active")
    ]

    return {
        "date": date,
        "professionals": professionals,
        "slots": {}
    }

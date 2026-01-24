from datetime import datetime, timedelta
from auth.professionals_store import load_professionals


def build_slots(schedule):
    """
    Construye slots a partir del horario del profesional
    """
    slots = {}

    start = datetime.strptime(schedule["start"], "%H:%M")
    end = datetime.strptime(schedule["end"], "%H:%M")
    minutes = schedule["slotMinutes"]

    current = start
    while current < end:
        time_str = current.strftime("%H:%M")
        slots[time_str] = {
            "status": "free"
        }
        current += timedelta(minutes=minutes)

    return slots


def build_agenda(date: str):
    professionals_dict = load_professionals()

    professionals = [
        p for p in professionals_dict.values()
        if p.get("active")
    ]

    slots = {}

    for p in professionals:
        slots[p["id"]] = build_slots(p["schedule"])

    return {
        "date": date,
        "professionals": professionals,
        "slots": slots
    }

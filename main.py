import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================
# Routers
# ==========================

from auth.auth_service import login_router

from core.professionals_router import router as professionals_router  # 👨‍⚕️ GLOBAL

from agenda.router import router as agenda_router  # 📅 Agenda diaria
from agenda.summary_router import router as agenda_summary_router  # 📅 Resumen mensual/semanal
from agenda.professionals_router import router as professionals_admin_router
from modules.fichas.ficha_create import router as ficha_create_router
from modules.fichas.ficha_read import router as ficha_read_router
from modules.fichas.ficha_update import router as ficha_update_router
from api.gpt_clinical import router as gpt_clinical_router


# ==========================
# APP CORE
# ==========================

app = FastAPI(
    title="Ficha Clínica – Backend",
    version="1.0"
)

# ==========================
# CORS (por entorno)
# ==========================

FRONTEND_URL = os.getenv("FRONTEND_URL")

if not FRONTEND_URL:
    raise RuntimeError("Falta variable FRONTEND_URL en Render")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# ROUTERS
# ==========================

# 🔐 Auth
app.include_router(login_router)

# 👨‍⚕️ Profesionales globales (ADMIN)
app.include_router(professionals_router)

# 📅 Agenda diaria
app.include_router(agenda_router)

# 📅 Agenda resumen (calendario mensual/semanal)
app.include_router(agenda_summary_router)

app.include_router(professionals_admin_router)

app.include_router(ficha_create_router)
app.include_router(ficha_read_router)
app.include_router(ficha_update_router)

# 🤖 GPT clínico
app.include_router(gpt_clinical_router)

# ==========================
# HEALTHCHECK
# ==========================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Ficha Clínica Backend",
        "modules": [
            "auth",
            "professionals",
            "agenda",
            "agenda-summary"
        ]
    }

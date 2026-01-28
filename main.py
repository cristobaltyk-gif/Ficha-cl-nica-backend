import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================
# Routers
# ==========================

from auth.auth_service import login_router
from agenda.router import router as agenda_router  # ✅ Agenda diaria
from agenda.summary_router import router as agenda_summary_router  # ✅ Resumen mensual/semanal
from core.professionals_router import router as professionals_router
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

# 📅 Agenda diaria
app.include_router(agenda_router)

# 📅 Agenda resumen (calendario mensual/semanal)
app.include_router(agenda_summary_router)

# 👨‍⚕️ Profesionales globales (ADMIN)
app.include_router(professionals_router)

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
            "agenda",
            "agenda-summary"
        ]
    }

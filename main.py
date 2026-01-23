import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers (módulos separados)
from auth.auth_service import login_router
from routes.agenda_router import agenda_router

# ======================================================
# APP CORE (ORQUESTADOR)
# ======================================================

app = FastAPI(
    title="Ficha Clínica – Backend",
    version="0.1"
)

# ======================================================
# CORS (POR ENTORNO)
# ======================================================

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

# ======================================================
# ROUTERS (ORQUESTACIÓN PURA)
# ======================================================

# 🔐 Login
app.include_router(login_router)

# 📅 Agenda secretaria
app.include_router(agenda_router)

# ======================================================
# HEALTHCHECK
# ======================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Ficha Clínica Backend"
    }

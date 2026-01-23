import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_service import login_router

app = FastAPI(
    title="Ficha Clínica – Backend",
    version="0.1"
)

# ✅ ORIGEN DESDE ENTORNO
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

# 🔐 Auth
app.include_router(login_router)

@app.get("/")
def root():
    return {"status": "ok"}

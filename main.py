from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_service import login_router

app = FastAPI(
    title="Ficha Clínica – Backend",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego se restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Auth
app.include_router(login_router)

@app.get("/")
def root():
    return {"status": "ok"}

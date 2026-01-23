from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.auth_service import login_router

app = FastAPI(
    title="Ficha Clínica – Backend",
    version="0.1"
)

# ✅ CORS CORRECTO (FastAPI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ficha-cl-nica-ica-fronted-towr-81ykwv7y2.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Auth
app.include_router(login_router)

@app.get("/")
def root():
    return {"status": "ok"}

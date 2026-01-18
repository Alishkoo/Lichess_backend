from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.auth.router import router as auth_router
from src.profile.router import router as profile_router
from src.games.router import router as games_router

app = FastAPI(
    title="Lichess Stats API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(games_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

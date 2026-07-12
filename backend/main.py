"""
FastAPI application entrypoint.

Run locally with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, auth, chat, pull_requests, repositories, reports
from app.core.config import settings
from app.core.database import init_db

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered GitHub repository review platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Dev convenience: creates tables if they don't exist. Use Alembic
    # migrations in production instead of relying on this.
    init_db()


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(repositories.router, prefix=settings.API_V1_PREFIX)
app.include_router(analyses.router, prefix=settings.API_V1_PREFIX)
app.include_router(pull_requests.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)

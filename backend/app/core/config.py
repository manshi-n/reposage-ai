"""
Application configuration.

All values are read from environment variables (see .env.example at the
project root). Nothing here is hard-coded that shouldn't be.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    APP_NAME: str = "RepoSage AI"
    ENV: str = "development"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    JWT_SECRET_KEY: str = ""
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./reposage.db"

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- GitHub OAuth ---
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_CALLBACK_URL: str = "http://localhost:8000/api/v1/auth/github/callback"
    GITHUB_FRONTEND_CALLBACK_URL: str = "http://localhost:5173/auth/github/callback"
    TOKEN_ENCRYPTION_KEY: str = ""

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- Vector store ---
    VECTOR_DB_PATH: str = "./data/chroma"

    # --- JWT ---
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 0

    # --- Repository analysis safety limits (see security requirements) ---
    MAX_REPO_SIZE_MB: int = 500
    MAX_FILES: int = 5000
    MAX_FILE_SIZE_KB: int = 1024
    CLONE_TIMEOUT_SECONDS: int = 120
    ANALYSIS_TASK_TIMEOUT_SECONDS: int = 900
    CLONE_TMP_DIR: str = "/tmp/reposage-clones"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

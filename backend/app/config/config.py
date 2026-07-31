import os
from pathlib import Path
from functools import lru_cache
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    APP_VERSION: str = "1.0.0"
    APP_NAME: str = "Misinformation Velocity Tracker"
    APP_DESCRIPTION: str = (
        "Track how a claim spreads and mutates across public platforms in Nepal — "
        "mutation tree, velocity, and an explainable verdict for fact-checkers."
    )
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = ""
    TEST_DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./test_app.db"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    API_PREFIX: str = "/api"

    # --- Supabase ---
    # Service-role key is server-side only (loaders / privileged API calls).
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # --- Gemini (embeddings + reasoning) ---
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 768
    GENERATION_MODEL: str = "gemini-1.5-flash"

    # --- Authenticated claim ingestion ---
    CLAIM_MATCH_THRESHOLD: float = Field(default=0.85, ge=0, le=1)
    CLAIM_MATCH_WINDOW_DAYS: int = Field(default=3650, ge=1, le=36500)
    CLAIM_RATE_LIMIT: int = Field(default=10, ge=1, le=1000)
    CLAIM_RATE_WINDOW_MINUTES: int = Field(default=60, ge=1, le=10080)

    # --- Loader / generator limits ---
    NEPOC_CLAIM_GROUPS: int = 10
    MISDETECT_ROWS_PER_DOMAIN: int = 5
    CHHATRAMANI_ROOT_CLAIMS: int = 25
    VARIANTS_PER_ROOT: int = 6

    # Database settings
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False
    DB_SSL_MODE: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


BASE_DIR = Path(__file__).parent.parent

# Logging configuration
LOGGING_CONFIG = {
    "development": {
        "log_level": "DEBUG",
        "log_dir": BASE_DIR / "logs" / "dev",
    },
    "production": {
        "log_level": "INFO",
        "log_dir": BASE_DIR / "logs" / "prod",
    },
    "testing": {
        "log_level": "DEBUG",
        "log_dir": None,  # Console only
    },
}

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
# Ensure environment is one of the defined keys, default to development if not
if ENVIRONMENT not in LOGGING_CONFIG:
    ENVIRONMENT = "development"
CURRENT_LOGGING_CONFIG = LOGGING_CONFIG[ENVIRONMENT]

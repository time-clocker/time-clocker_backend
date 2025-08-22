# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import json

class Settings(BaseSettings):
    APP_NAME: str = "WorkTime API"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"

    DATABASE_URL: str
    FIREBASE_WEB_API_KEY: str | None = None

    FIREBASE_PROJECT_ID: str
    FIREBASE_CREDENTIALS_JSON: Optional[str] = Field(default=None)
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(default=None)

    DEFAULT_TIMEZONE: str = "America/Bogota"
    DEFAULT_HOURLY_RATE: float = 15000.0

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def firebase_credentials_dict(self) -> dict:
        if self.FIREBASE_CREDENTIALS_JSON:
            return json.loads(self.FIREBASE_CREDENTIALS_JSON)
        return {}

settings = Settings()

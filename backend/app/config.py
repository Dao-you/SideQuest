"""Application Configuration using Pydantic Settings."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global Application Settings."""
    
    # App basic info
    APP_NAME: str = "SideQuest Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Google Gemini AI Config
    GEMINI_API_KEY: str = Field(default="", description="Google AI Studio Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-3.7-flash", description="Gemini Model Identifier (e.g. gemini-3.7-flash, gemini-2.5-flash, gemini-3.1-pro)")

    # Google Maps & Auth Config
    GOOGLE_MAPS_API_KEY: str = Field(default="", description="Google Maps Platform API Key")
    GOOGLE_CLIENT_ID: str = Field(
        default="917216410511-1tupuplbm4bnr76j7g9r4uii8i84olru.apps.googleusercontent.com",
        description="Google OAuth 2.0 Web Client ID",
    )

    # GCP / Firestore Config
    GCP_PROJECT_ID: str = Field(default="", description="Google Cloud Project ID")
    FIRESTORE_DATABASE: str = Field(default="(default)", description="Firestore Database Name")
    FIRESTORE_EMULATOR_HOST: str = Field(default="", description="Firestore Emulator Host if local")

    # CORS Config
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,*"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins into a list."""
        if not self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

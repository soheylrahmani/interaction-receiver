from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+psycopg2://interaction_receiver:change_me@localhost:5432/interaction_receiver"

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Interaction Receiver"

    # Server Settings
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "production"

    # Comma-separated list of allowed CORS origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080,http://localhost:8000"

    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None

    # AvalAI.ir (optional)
    AVALAI_API_KEY: Optional[str] = None
    AVALAI_API_KEY_4O: Optional[str] = None
    AVALAI_BASE_URL: str = "https://api.avalapis.ir/v1"
    AVALAI_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

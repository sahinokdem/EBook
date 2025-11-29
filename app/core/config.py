"""
Config - Updated.

Yeni ayarlar:
- Celery (Redis)
- PDF processing
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str
    
    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "eBook API"
    DEBUG: bool = False
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    
    # Celery / Redis
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False  # Development'ta False
    
    # PDF Processing
    PDF_MAX_PAGES: int = 1000  # Maksimum sayfa limiti
    PDF_HEADING_H1_SIZE: float = 18.0
    PDF_HEADING_H2_SIZE: float = 14.0
    PDF_HEADING_H3_SIZE: float = 12.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
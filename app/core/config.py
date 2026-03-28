from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import field_validator #

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str

    # Render/SQLAlchemy Fix: postgres:// -> postgresql://
    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
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
    USE_CELERY: bool = False
    
    # PDF Processing
    PDF_MAX_PAGES: int = 1000
    PDF_HEADING_H1_SIZE: float = 18.0
    PDF_HEADING_H2_SIZE: float = 14.0
    PDF_HEADING_H3_SIZE: float = 12.0

    # Vector DB (Qdrant)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "ebook_blocks"

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview" # [cite: 2026-03-28]
    GEMINI_TEMPERATURE: float = 0.4
    GEMINI_MAX_TOKENS: int = 8192
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
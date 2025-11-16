from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings - Environment variables'lardan otomatik okur.
    
    Pydantic Settings kullanmanın avantajları:
    1. Type validation (int, bool, str otomatik parse eder)
    2. .env dosyasından otomatik okur
    3. IDE autocomplete desteği
    4. Immutable (güvenli)
    """
    
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
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB
    
    class Config:
        """
        Pydantic config - .env dosyasını otomatik okur.
        case_sensitive=False → büyük/küçük harf farketmez
        """
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Settings singleton - Sadece bir kez oluşturulur.
    
    @lru_cache() decorator sayesinde:
    - İlk çağrıda Settings() create edilir
    - Sonraki çağrılarda cache'den döner (performans)
    - Memory efficient
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Kolayca import etmek için
settings = get_settings()
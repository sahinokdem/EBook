from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional


"""
Pydantic Schemas - Request/Response validation için kullanılır.

SQLAlchemy Models vs Pydantic Schemas:
- SQLAlchemy: Database ile konuşur (ORM)
- Pydantic: API request/response validation (serialization/deserialization)

Örnek akış:
1. Client JSON gönderir → Pydantic validate eder
2. Pydantic → SQLAlchemy model'e dönüştürülür
3. Database'e kaydedilir
4. Database'den okunur → SQLAlchemy model
5. SQLAlchemy → Pydantic'e dönüştürülür
6. Client'a JSON olarak döner
"""


class UserBase(BaseModel):
    """
    Base schema - Ortak fieldlar burada.
    
    DRY (Don't Repeat Yourself) prensibi:
    - email ve username birçok schema'da kullanılır
    - Tek yerde tanımla, diğerleri inherit etsin
    """
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    
    """
    EmailStr: Pydantic'in özel tipi, email validation yapar
    Field(..., min_length=3): 
        - ... → Required (zorunlu)
        - min_length/max_length → Validation rules
    """


class UserCreate(UserBase):
    """
    Sign up request schema.
    
    Client gönderir:
    {
        "email": "user@example.com",
        "username": "johndoe",
        "password": "SecurePass123!"
    }
    """
    password: str = Field(..., min_length=8, max_length=100)
    
    """
    Password kuralları:
    - Minimum 8 karakter (güvenlik için)
    - Maksimum 100 karakter (bcrypt limiti)
    - Plain text olarak gelir, hash'lenip kaydedilir
    """


class UserLogin(BaseModel):
    """
    Login request schema.
    
    Client gönderir:
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    
    Not: username yerine email ile login (daha yaygın)
    İleride username ile de login eklenebilir
    """
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """
    User response schema - Client'a dönülen data.
    
    Response'da PASSWORD ASLA YOK!
    
    API döner:
    {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "is_active": true,
        "created_at": "2024-11-15T19:30:00Z"
    }
    """
    id: int
    is_active: bool
    created_at: datetime
    
    # Pydantic v2 config
    model_config = ConfigDict(from_attributes=True)
    
    """
    from_attributes=True (Pydantic v2):
    - SQLAlchemy model'den otomatik dönüşüm
    - Eskiden: orm_mode=True (Pydantic v1)
    
    Örnek:
        user = User(id=1, email="test@test.com", ...)  # SQLAlchemy
        return UserResponse.from_orm(user)  # Pydantic'e dönüştür
    
    from_attributes sayesinde SQLAlchemy model'in attribute'larını okur
    """


class Token(BaseModel):
    """
    JWT token response schema.
    
    Login başarılı olduğunda döner:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    """
    access_token: str
    token_type: str = "bearer"
    
    """
    token_type: OAuth2 standardı (her zaman "bearer")
    Client bunu header'da kullanır: Authorization: Bearer <token>
    """


class TokenData(BaseModel):
    """
    JWT token payload schema - Token decode edilince içindeki data.
    
    Token içeriği:
    {
        "sub": "123",  # subject (user_id)
        "exp": 1234567890  # expiration (otomatik handle edilir)
    }
    
    Bu schema sadece internal kullanım için (token validation)
    """
    user_id: Optional[int] = None
    
    """
    Optional[int]: Token invalid olabilir, user_id None olabilir
    Validation sırasında kontrol edilir
    """
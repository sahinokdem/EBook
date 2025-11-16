from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from typing import Optional

from app.users import repository
from app.users.schemas import UserCreate, Token
from app.users.models import User
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token
)
from app.core.config import settings


"""
Service Layer - Business Logic.

Repository vs Service:
- Repository: Sadece CRUD (get, create, update, delete)
- Service: Business rules + validation + repository kullanımı

Örnek:
- Repository: create_user(email, username, hashed_password)
- Service: register_user(UserCreate) → email check, password hash, create_user()

Service Layer Pattern avantajları:
- Business logic tek yerde
- Repository'yi wrapper'lar (abstraction)
- Validation ve error handling
- Transaction yönetimi
"""


def register_user(db: Session, user_data: UserCreate) -> User:
    """
    Yeni user kaydı oluştur.
    
    Business rules:
    1. Email zaten kullanılıyor mu kontrol et
    2. Username zaten kullanılıyor mu kontrol et
    3. Password'ü hash'le
    4. User'ı database'e kaydet
    
    Args:
        db: Database session
        user_data: UserCreate schema (email, username, password)
        
    Returns:
        User: Oluşturulan user
        
    Raises:
        HTTPException 400: Email veya username zaten kullanılıyorsa
    """
    
    # 1. Email kontrolü
    existing_user = repository.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    """
    HTTPException nedir?
    - FastAPI'nin özel exception'ı
    - Otomatik olarak JSON response döner
    - status_code ve detail verebilirsin
    
    Response:
    {
        "detail": "Email already registered"
    }
    HTTP Status: 400 Bad Request
    """
    
    # 2. Username kontrolü
    existing_user = repository.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # 3. Password'ü hash'le
    hashed_password = get_password_hash(user_data.password)
    
    """
    Security best practice:
    - Plain password ASLA database'e kaydetme
    - Hash one-way (geri döndürülemez)
    - Bcrypt kullan (yavaş → brute force zor)
    """
    
    # 4. User oluştur
    new_user = repository.create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> Token:
    """
    User authentication - Login.
    
    Business rules:
    1. Email ile user bul
    2. Password doğru mu kontrol et
    3. User aktif mi kontrol et
    4. JWT token oluştur ve döndür
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        
    Returns:
        Token: JWT access token
        
    Raises:
        HTTPException 401: Email/password yanlış veya user inactive
    """
    
    # 1. User'ı bul
    user = repository.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    """
    Security note:
    "Email not found" yerine "Incorrect email or password" deriz
    
    Neden?
    - Attacker email'in var olup olmadığını öğrenmesin
    - User enumeration saldırısını engelle
    
    WWW-Authenticate header:
    - OAuth2 standardı
    - Client'a "Bearer token gönder" der
    """
    
    # 2. Password kontrolü
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 3. User aktif mi?
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    """
    is_active kontrolü:
    - Email verification bekleniyor olabilir
    - Admin tarafından ban edilmiş olabilir
    - Hesap geçici olarak suspend edilmiş olabilir
    """
    
    # 4. JWT token oluştur
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},  # subject = user_id
        expires_delta=access_token_expires
    )
    
    """
    Token payload:
    {
        "sub": "123",  # User ID (string olarak)
        "exp": 1234567890  # Expiration timestamp
    }
    
    "sub" nedir?
    - JWT standardı: "subject" (token'ın sahibi)
    - Genelde user ID kullanılır
    """
    
    return Token(access_token=access_token, token_type="bearer")


def get_current_user(db: Session, token: str) -> User:
    """
    JWT token'dan current user'ı al.
    
    Bu fonksiyon protected endpoints için kullanılır.
    Dependency injection ile her request'te çalışır.
    
    Args:
        db: Database session
        token: JWT access token
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException 401: Token invalid veya user bulunamadı
    """
    from jose import JWTError
    from app.core.security import verify_token
    
    # Token'ı doğrula ve decode et
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    """
    Token invalid olabilir:
    - Signature yanlış (token değiştirilmiş)
    - Expired (geçerlilik süresi dolmuş)
    - Format yanlış
    """
    
    # Token payload'dan user_id al
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # User'ı database'den al
    user = repository.get_user_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    """
    User neden bulunamayabilir?
    - User silinmiş olabilir (ama token hala valid)
    - Database'den veri silinmiş
    
    Bu yüzden her request'te database'den user'ı kontrol ederiz
    """
    
    # User aktif mi?
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user
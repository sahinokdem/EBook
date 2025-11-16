from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings


# Password hashing context - bcrypt algoritması kullanır
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

"""
Bcrypt nedir?
- Password hashing algoritması
- Yavaş tasarlanmıştır (brute force saldırılarına karşı)
- Salt otomatik ekler (aynı password farklı hash'ler üretir)
- One-way encryption (geri döndürülemez)

Örnek:
password: "hello123"
hash: "$2b$12$KIXqz.../aHdj2kla..."  (her seferinde farklı)
"""


def get_password_hash(password: str) -> str:
    """
    Plain text password'ü hash'e çevirir.
    
    Neden hash'leriz?
    - Database çalınırsa passwordler açıkta kalmaz
    - Adminler bile göremez
    - Security best practice
    
    Args:
        password: Plain text password (örn: "MyPass123!")
        
    Returns:
        str: Hashed password (örn: "$2b$12$...")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Plain text password ile hash'i karşılaştırır.
    
    Nasıl çalışır?
    - Plain password'ü hash'ler
    - Database'deki hash ile karşılaştırır
    - Salt otomatik handle edilir
    
    Args:
        plain_password: User'ın girdiği password
        hashed_password: Database'de saklanan hash
        
    Returns:
        bool: Eşleşiyorsa True, değilse False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT access token oluşturur.
    
    JWT nedir?
    - JSON Web Token - üç parçadan oluşur: header.payload.signature
    - Self-contained (tüm bilgi token içinde)
    - Stateless (server'da session tutmaya gerek yok)
    - Signature ile doğrulanır (değiştirilemez)
    
    Token içeriği (payload):
    {
        "sub": "user_id",  # Subject (genelde user ID)
        "exp": 1234567890  # Expiration time (Unix timestamp)
    }
    
    Args:
        data: Token'a eklenecek data (örn: {"sub": user.id})
        expires_delta: Token geçerlilik süresi (None ise default 30 dakika)
        
    Returns:
        str: JWT token (örn: "eyJhbGc...")
    """
    to_encode = data.copy()  # Original data'yı değiştirmemek için copy
    
    # Expiration time hesapla
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Payload'a expiration ekle
    to_encode.update({"exp": expire})
    
    # Token'ı encode et (secret key ile imzala)
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    JWT token'ı doğrular ve payload'u döner.
    
    Doğrulama adımları:
    1. Signature check (token değiştirilmiş mi?)
    2. Expiration check (token geçerliliğini yitirmiş mi?)
    3. Payload'u decode et
    
    Args:
        token: JWT token
        
    Returns:
        dict: Token payload'u ({"sub": user_id, "exp": ...})
        None: Token geçersizse
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        # Token geçersiz (signature yanlış, expired, vb.)
        return None
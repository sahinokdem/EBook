from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.shared.database import SessionLocal
from app.users.models import User
from app.users import service


"""
Dependency Injection - FastAPI'nin en güçlü özelliklerinden biri.

Nedir?
- Fonksiyonlara otomatik parametre enjekte eder
- Code reusability++
- Testing kolaylaşır (mock yapılabilir)
- Clean code

Örnek:
    @router.get("/users/me")
    def get_me(current_user: User = Depends(get_current_user)):
        return current_user
    
    FastAPI otomatik olarak:
    1. get_current_user() fonksiyonunu çağırır
    2. Sonucu current_user parametresine atar
    3. Route handler çalışır
"""


# HTTP Bearer Token scheme - JWT authentication için
security = HTTPBearer()

"""
HTTPBearer nedir?
- FastAPI'nin OAuth2 Bearer token scheme'i
- Authorization header'ından token'ı otomatik çıkarır
- Header formatı: Authorization: Bearer <token>

Swagger UI'da otomatik olarak "Authorize" butonu oluşturur
"""


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Her request için yeni bir session oluşturur.
    Request bitince session otomatik close edilir.
    
    Yields:
        Session: Database session
        
    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
    """
    Generator pattern (yield):
    - yield'den önce: Setup (session oluştur)
    - yield: Session'ı route handler'a ver
    - yield'den sonra: Cleanup (session kapat)
    
    Neden finally?
    - Exception olsa bile session mutlaka close edilir
    - Connection leak engellenir
    - Database connection pool sağlıklı kalır
    """


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Current authenticated user dependency.
    
    JWT token'dan user'ı çıkarır ve döndürür.
    Protected endpoints için kullanılır.
    
    Args:
        credentials: HTTP Bearer token (otomatik extract edilir)
        db: Database session (dependency)
        
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException 401: Token invalid veya user bulunamadı
        
    Usage:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}
    """
    
    # Token'ı al (Bearer kısmı otomatik çıkarılır)
    token = credentials.credentials
    
    """
    credentials.credentials nedir?
    - Header: Authorization: Bearer abc123xyz
    - credentials.credentials = "abc123xyz"
    
    HTTPBearer otomatik olarak:
    1. Authorization header'ını okur
    2. "Bearer " prefix'ini çıkarır
    3. Token'ı credentials.credentials'a atar
    """
    
    # Service layer'ı kullanarak user'ı al
    user = service.get_current_user(db, token)
    
    """
    service.get_current_user():
    1. Token'ı validate eder
    2. User ID'yi extract eder
    3. Database'den user'ı çeker
    4. User aktif mi kontrol eder
    5. User'ı döndürür veya HTTPException fırlatır
    """
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Current active user dependency.
    
    get_current_user'ın wrapper'ı - ekstra is_active kontrolü.
    Genelde get_current_user yeterli ama bu da opsiyonel olarak kullanılabilir.
    
    Args:
        current_user: Authenticated user (dependency)
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException 400: User inactive ise
        
    Usage:
        @router.get("/admin-only")
        def admin_route(current_user: User = Depends(get_current_active_user)):
            # Sadece aktif userlar buraya erişebilir
            return {"message": "Admin area"}
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
    
    """
    Not: Aslında service.get_current_user() zaten is_active kontrolü yapıyor.
    Bu fonksiyon redundant ama gösterim amaçlı bırakıyorum.
    
    İleride farklı user rolleri eklenebilir:
    - get_current_admin_user()
    - get_current_premium_user()
    - etc.
    """


"""
Dependency Chain (Zincirleme):

get_current_active_user
    ↓ depends on
get_current_user
    ↓ depends on
security (HTTPBearer) + get_db
    ↓ depends on
SessionLocal

FastAPI otomatik olarak tüm dependency chain'i çözer:
1. Database session oluşturur
2. Token'ı extract eder
3. User'ı database'den çeker
4. Tüm validation'ları yapar
5. Route handler'a user'ı pass eder

Tek satır kod:
    current_user: User = Depends(get_current_user)
    
Bu kadar! 🎉
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.shared.dependencies import get_db, get_current_user
from app.users.schemas import UserCreate, UserResponse, UserLogin, Token
from app.users.models import User
from app.users import service


"""
APIRouter - Endpoint grupları oluşturmak için.

Neden Router?
- Modüler yapı (her domain kendi router'ı)
- Prefix ekleme (/auth, /users, etc.)
- Tag ekleme (Swagger UI'da gruplandırma)
- Dependency paylaşımı

main.py'de tüm router'lar toplanır:
    app.include_router(users_router)
    app.include_router(books_router)
"""

router = APIRouter()

"""
APIRouter() oluşturuldu.
main.py'de şöyle kullanılacak:
    app.include_router(router, prefix="/auth", tags=["Authentication"])
"""


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create new user account - Sign up endpoint.
    
    Public endpoint - Authentication gerekmez.
    
    Request Body:
    ```json
    {
        "email": "user@example.com",
        "username": "johndoe",
        "password": "SecurePass123!"
    }
    ```
    
    Response (201 Created):
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "is_active": true,
        "created_at": "2024-11-15T19:30:00Z"
    }
    ```
    
    Errors:
    - 400: Email already registered
    - 400: Username already taken
    - 422: Validation error (invalid email, short password, etc.)
    """
    
    """
    @router.post() decorator:
    - POST /signup endpoint oluşturur
    - response_model=UserResponse: Response Pydantic schema (password exclude)
    - status_code=201: Başarılı resource creation için standart
    
    user_data: UserCreate:
    - Request body'den otomatik parse edilir
    - Pydantic validation otomatik çalışır
    - Invalid data varsa 422 Unprocessable Entity döner
    
    db: Session = Depends(get_db):
    - Dependency injection
    - Her request için yeni session
    """
    
    new_user = service.register_user(db, user_data)
    return new_user
    
    """
    Return type:
    - new_user: SQLAlchemy User model
    - response_model=UserResponse: Pydantic schema'ya otomatik convert
    - from_attributes=True sayesinde dönüşüm çalışır
    
    Password response'da yok! (UserResponse'da tanımlı değil)
    """


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    User authentication - Login endpoint.
    
    Public endpoint - Authentication gerekmez.
    
    Request Body:
    ```json
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }
    ```
    
    Response (200 OK):
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```
    
    Token kullanımı:
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    
    Errors:
    - 401: Incorrect email or password
    - 401: Inactive user
    - 422: Validation error (invalid email format, etc.)
    """
    token = service.authenticate_user(
        db, 
        user_credentials.email, 
        user_credentials.password
    )
    return token
    
    """
    Login flow:
    1. User email + password gönderir
    2. service.authenticate_user():
       - User'ı bulur
       - Password'ü verify eder
       - JWT token oluşturur
    3. Token client'a döner
    4. Client token'ı her request'te gönderir
    """


@router.post("/logout")
def logout():
    """
    User logout endpoint.
    
    JWT stateless olduğu için server-side logout gereksiz.
    Client-side token'ı silmesi yeterli.
    
    Bu endpoint opsiyonel - gösterim amaçlı.
    
    Response (200 OK):
    ```json
    {
        "message": "Successfully logged out"
    }
    ```
    
    Not: Gerçek logout için client:
    1. localStorage'dan token'ı siler
    2. Authorization header'ını kaldırır
    """
    return {"message": "Successfully logged out"}
    
    """
    JWT ile logout problemi:
    - Token server'da tutulmaz (stateless)
    - Expire olana kadar geçerlidir
    - Gerçek logout için:
      1. Token blacklist tutulabilir (Redis)
      2. Refresh token kullanılabilir
      3. Kısa expiration time (30 dakika)
    
    Basit projeler için client-side logout yeterli.
    """


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Protected endpoint - JWT token gerekli.
    
    Headers:
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    
    Response (200 OK):
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "username": "johndoe",
        "is_active": true,
        "created_at": "2024-11-15T19:30:00Z"
    }
    ```
    
    Errors:
    - 401: Missing or invalid token
    - 401: User not found
    - 401: Inactive user
    """
    return current_user
    
    """
    current_user: User = Depends(get_current_user):
    - Dependency injection
    - Token otomatik validate edilir
    - User otomatik fetch edilir
    - Hiç manuel işlem yok!
    
    Bu endpoint kullanım alanları:
    - Frontend'de user bilgilerini göster
    - Profile page
    - "Logged in as..." mesajı
    """


"""
Router Summary:

Public Endpoints (Authentication gerekmez):
- POST /signup  → Yeni hesap oluştur
- POST /login   → Giriş yap, token al
- POST /logout  → Çıkış yap (client-side)

Protected Endpoints (JWT token gerekli):
- GET /me       → Current user bilgilerini al

main.py'de şöyle kullanılacak:
    app.include_router(
        users_router, 
        prefix="/api/v1/auth",  # /api/v1/auth/signup, /api/v1/auth/login
        tags=["Authentication"]  # Swagger UI'da gruplandırma
    )
"""
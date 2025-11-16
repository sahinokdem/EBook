from sqlalchemy.orm import Session
from app.users.models import User
from typing import Optional


"""
Repository Pattern - Database CRUD operations.

Neden Repository?
- Business logic'ten database logic'i ayırır (Separation of Concerns)
- Tek bir yerde tüm DB işlemleri (maintainability++)
- Test edilmesi kolay (mock yapılabilir)
- Query'leri tekrar kullanabilirsin

Repository vs Service:
- Repository: Sadece DB işlemleri (CREATE, READ, UPDATE, DELETE)
- Service: Business logic + Repository'yi kullanır
"""


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Email ile user bul.
    
    Kullanım alanları:
    - Login (email + password check)
    - Sign up (email zaten var mı kontrol)
    
    Args:
        db: Database session
        email: User email
        
    Returns:
        User: User bulunduysa User object
        None: User bulunamadıysa None
    """
    return db.query(User).filter(User.email == email).first()
    
    """
    SQLAlchemy Query:
    - db.query(User): SELECT * FROM users
    - .filter(User.email == email): WHERE email = 'given_email'
    - .first(): İlk sonucu getir (veya None)
    
    SQL equivalent:
    SELECT * FROM users WHERE email = 'given_email' LIMIT 1;
    """


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Username ile user bul.
    
    Kullanım alanları:
    - Sign up (username zaten var mı kontrol)
    - Profile lookup
    
    Args:
        db: Database session
        username: Username
        
    Returns:
        User: User bulunduysa User object
        None: User bulunamadıysa None
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    ID ile user bul.
    
    Kullanım alanları:
    - JWT token'dan user_id alınca user bilgilerini getir
    - Protected endpoints (current user)
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        User: User bulunduysa User object
        None: User bulunamadıysa None
    """
    return db.query(User).filter(User.id == user_id).first()
    
    """
    Alternatif (daha kısa):
    return db.query(User).get(user_id)
    
    Ama .get() deprecated oldu SQLAlchemy 2.0'da
    """


def create_user(db: Session, email: str, username: str, hashed_password: str) -> User:
    """
    Yeni user oluştur.
    
    IMPORTANT: Password zaten hash'lenmiş olarak gelir!
    Bu fonksiyon hash'leme yapmaz (Service layer'ın sorumluluğu)
    
    Args:
        db: Database session
        email: User email
        username: Username
        hashed_password: HASHED password (plain text değil!)
        
    Returns:
        User: Oluşturulan user object
    """
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    
    """
    User object oluştur (SQLAlchemy model)
    Henüz database'e kaydedilmedi!
    """
    
    db.add(db_user)
    """
    Session'a ekle (staging area)
    Henüz database'e commit edilmedi
    """
    
    db.commit()
    """
    Transaction'ı commit et → Database'e kaydet
    
    Neden commit?
    - Atomicity (all or nothing)
    - Rollback yapabilme şansı
    - Multiple operations birlikte commit edilebilir
    """
    
    db.refresh(db_user)
    """
    Database'den yeni değerleri al (id, timestamps, etc.)
    
    Neden refresh?
    - id otomatik generate edilir (auto-increment)
    - created_at, updated_at server tarafından set edilir
    - Fresh data döndürmek için
    """
    
    return db_user


def update_user(db: Session, user: User) -> User:
    """
    User'ı güncelle.
    
    Şu anda kullanılmıyor ama ileride gerekebilir:
    - Profile update
    - Email change
    - Username change
    
    Args:
        db: Database session
        user: Updated user object
        
    Returns:
        User: Updated user object
    """
    db.commit()
    db.refresh(user)
    return user
    
    """
    Kullanım:
        user = get_user_by_id(db, user_id)
        user.username = "new_username"
        updated_user = update_user(db, user)
    
    SQLAlchemy object tracking yapıyor:
    - user.username değiştirilince dirty olarak işaretler
    - commit() çağrılınca UPDATE query çalıştırır
    """


def delete_user(db: Session, user: User) -> None:
    """
    User'ı sil.
    
    IMPORTANT: Cascade="all, delete-orphan" sayesinde:
    - User silinince o user'ın kitapları da silinir
    - Orphan records kalmaz
    
    Args:
        db: Database session
        user: Silinecek user object
    """
    db.delete(user)
    db.commit()
    
    """
    SQL equivalent:
    DELETE FROM users WHERE id = user.id;
    
    Cascade sayesinde ayrıca:
    DELETE FROM books WHERE user_id = user.id;
    """
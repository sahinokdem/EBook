from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.shared.database import Base


class User(Base):
    """
    User model - Database'deki 'users' tablosunu temsil eder.
    
    SQLAlchemy ORM nedir?
    - Python class → Database table mapping
    - Column → Table column
    - Relationship → Foreign key ilişkileri
    
    Bu class'tan bir object oluşturduğumuzda → Database'e bir satır eklenir
    """
    
    __tablename__ = "users"  # Database'deki tablo ismi
    
    # Primary Key - Her user için unique ID
    id = Column(Integer, primary_key=True, index=True)
    """
    primary_key=True: Bu column primary key (her satır için unique)
    index=True: Bu column için index oluştur (arama performansı++)
    """
    
    # Email - Unique olmalı (aynı email ile 2 hesap açılmasın)
    email = Column(String(255), unique=True, index=True, nullable=False)
    """
    unique=True: Aynı email 2 kez kullanılamaz
    index=True: Email ile arama hızlı olur (login için önemli)
    nullable=False: Boş olamaz (zorunlu alan)
    String(255): Maksimum 255 karakter
    """
    
    # Username - Unique ve zorunlu
    username = Column(String(100), unique=True, index=True, nullable=False)
    
    # Hashed Password - Plain text değil!
    hashed_password = Column(String(255), nullable=False)
    """
    Dikkat: Password'ü direkt kaydetmiyoruz!
    Bcrypt ile hash'lenmiş hali kaydedilir
    """
    
    # Account status - Hesap aktif mi?
    is_active = Column(Boolean, default=True, nullable=False)
    """
    default=True: Yeni user oluşturulduğunda otomatik True olur
    İleride email verification eklenirse False yapılabilir
    """
    
    # Timestamps - Oluşturma ve güncelleme zamanları
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    """
    server_default=func.now(): Database server'ın timestamp'ini kullan
    timezone=True: Timezone bilgisi de sakla (UTC önerili)
    func.now(): SQLAlchemy function - SQL NOW() demek
    """
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    """
    onupdate=func.now(): Her update'de otomatik güncelle
    Örnek: User email'i değiştirildiğinde updated_at otomatik güncellenir
    """
    
    # Relationships - User'ın kitapları (One-to-Many)
    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")
    """
    relationship() nedir?
    - Python tarafında ilişki kurar (SQL foreign key değil!)
    - user.books → User'ın tüm kitaplarını getirir
    - Lazy loading (kitaplar sadece erişilince yüklenir)
    
    "Book": İlişkili model (string olarak, henüz tanımlanmamış olabilir)
    back_populates="owner": Book model'deki 'owner' field'ı ile eşleşir
    cascade="all, delete-orphan": User silinince kitapları da sil
    
    Cascade options:
    - "all": Tüm işlemler propagate olur (save, delete, etc.)
    - "delete-orphan": Parent'ı olmayan childları sil
    Örnek: User silinince, o user'ın kitapları da silinir
    """
    
    def __repr__(self) -> str:
        """
        Object'in string representation'ı (debugging için yararlı)
        
        Returns:
            str: User(id=1, email='user@example.com', username='john')
        """
        return f"User(id={self.id}, email='{self.email}', username='{self.username}')"
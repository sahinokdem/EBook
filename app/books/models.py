from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.shared.database import Base


class Book(Base):
    """
    Book model - Database'deki 'books' tablosunu temsil eder.
    
    Her kitap bir user'a aittir (Many-to-One relationship)
    """
    
    __tablename__ = "books"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Book metadata
    title = Column(String(500), nullable=False, index=True)
    """
    index=True: Title ile arama yapmak için (search functionality)
    String(500): Uzun kitap isimleri için
    """
    
    author = Column(String(255), nullable=True)
    """
    nullable=True: Author bilinmeyebilir (opsiyonel)
    """
    
    # File information
    file_path = Column(String(1000), nullable=False)
    """
    File'ın server'da nerede saklandığı
    Örnek: "uploads/user_123/book_456.pdf"
    String(1000): Uzun path'ler için yeterli
    """
    
    file_name = Column(String(500), nullable=False)
    """
    Original file name (user'ın upload ettiği isim)
    Örnek: "Harry Potter and the Philosopher's Stone.pdf"
    """
    
    file_size = Column(BigInteger, nullable=False)
    """
    BigInteger: Büyük dosyalar için (bytes cinsinden)
    Örnek: 52428800 (50MB)
    """
    
    file_type = Column(String(50), nullable=False)
    """
    MIME type veya extension
    Örnek: "application/pdf", "epub", etc.
    """
    
    # Foreign Key - Bu kitap hangi user'a ait?
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    """
    ForeignKey("users.id"): users tablosundaki id column'una referans
    index=True: user_id ile arama hızlı olur
    
    Foreign Key nedir?
    - İki tablo arasında ilişki kurar
    - Referential integrity sağlar (orphan records olmaz)
    - user_id, users.id'de olmayan bir değer olamaz
    """
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    """
    Book ne zaman upload edildi?
    server_default=func.now(): Upload anında otomatik set edilir
    """
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    """
    Book metadata'sı ne zaman güncellendi?
    Örnek: Title değiştirildiğinde updated_at güncellenir
    """
    
    # Relationship - Book'un owner'ı (Many-to-One)
    owner = relationship("User", back_populates="books")
    """
    relationship() - Python tarafında ilişki
    
    book.owner → Bu kitabın sahibi olan User object'i
    Örnek:
        book = Book.query.first()
        print(book.owner.email)  # User'ın email'i
    
    back_populates="books": User model'deki 'books' ile eşleşir
    
    Many-to-One nedir?
    - Birçok book → Bir user'a ait olabilir
    - Bir user → Birçok book'a sahip olabilir
    """
    
    def __repr__(self) -> str:
        """
        Object'in string representation'ı
        
        Returns:
            str: Book(id=1, title='...', owner_id=5)
        """
        return f"Book(id={self.id}, title='{self.title}', user_id={self.user_id})"
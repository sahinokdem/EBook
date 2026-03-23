from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.shared.database import Base
import enum


class BookStatus(str, enum.Enum):
    """
    Kitap işleme durumu.
    
    Upload → Processing → Completed/Failed
    """
    PENDING = "pending"          # Upload edildi, parse bekleniyor
    PROCESSING = "processing"    # Parse ediliyor
    COMPLETED = "completed"      # Parse tamamlandı, okunabilir
    FAILED = "failed"            # Parse başarısız


class Book(Base):
    """
    Book model - Güncellendi.
    
    Değişiklikler:
    - file_path kaldırıldı (PDF saklanmayacak)
    - status eklendi (parse durumu)
    - total_pages eklendi
    - pages relationship eklendi
    """
    
    __tablename__ = "books"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Book metadata
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    
    # File information (original file info - referans için)
    file_name = Column(String(500), nullable=False)
    """Original dosya adı (gösterim için)"""
    
    file_size = Column(Integer, nullable=False)
    """Original dosya boyutu (bytes)"""
    
    file_type = Column(String(50), nullable=False)
    """MIME type: application/pdf"""
    
    # Processing status
    status = Column(
        Enum(BookStatus), 
        default=BookStatus.PENDING, 
        nullable=False,
        index=True
    )
    """
    Parse durumu:
    - PENDING: Henüz parse edilmedi
    - PROCESSING: Parse ediliyor
    - COMPLETED: Tamamlandı
    - FAILED: Hata oluştu
    """
    
    error_message = Column(Text, nullable=True)
    """Parse hatası varsa mesajı"""
    
    # Page info
    total_pages = Column(Integer, nullable=True)
    """Toplam sayfa sayısı (parse sonrası set edilir)"""
    
    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    owner = relationship("User", back_populates="books")
    blocks = relationship(
        "BookBlock",
        back_populates="book", 
        cascade="all, delete-orphan",
        order_by="BookBlock.page_number, BookBlock.block_index"
    )
    """
    Book silinince tüm blokları da silinir (cascade)
    Bloklar page_number ve block_index'e göre sıralı gelir
    """

    @property
    def pages(self):
        """Geriye dönük uyumluluk için pages alias."""
        return self.blocks
    
    def __repr__(self) -> str:
        return f"Book(id={self.id}, title='{self.title}', status={self.status})"


class BookBlock(Base):
    """
    BookBlock model - Kitap içerik bloklarını saklar.

    Her blok:
    - Belirli bir sayfaya aittir
    - Sayfa içindeki sıra bilgisini (block_index) taşır
    - RAG için vector_id ile vector DB kaydıyla eşleşir
    """

    __tablename__ = "book_blocks"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key - Hangi kitaba ait?
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    """
    index=True: Kitabın sayfalarını hızlı çekmek için
    """
    
    # Position info
    page_number = Column(Integer, nullable=False)
    """
    Sayfa numarası (1'den başlar)
    """

    block_index = Column(Integer, nullable=False)
    """Sayfa içindeki blok sırası (0'dan başlar)."""
    
    # Content
    content = Column(Text, nullable=False)
    """
    Blok metni (text). RAG retrieval için normalize içerik tutulur.
    """

    vector_id = Column(String(64), nullable=True, unique=True, index=True)
    """Qdrant point ID eşleşmesi için UUID/string id."""
    
    # Metadata
    word_count = Column(Integer, nullable=False, default=0)
    """Sayfadaki kelime sayısı (okuma süresi hesabı için)"""
    
    char_count = Column(Integer, nullable=False, default=0)
    """Karakter sayısı"""
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship
    book = relationship("Book", back_populates="blocks")
    
    def __repr__(self) -> str:
        return (
            f"BookBlock(book_id={self.book_id}, page={self.page_number}, "
            f"block={self.block_index}, words={self.word_count})"
        )


# Geriye dönük uyumluluk (eski importlar için)
BookPage = BookBlock
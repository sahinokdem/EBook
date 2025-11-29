"""
Book Repository - Updated.

Değişiklikler:
- file_path parametresi kaldırıldı (PDF saklanmıyor)
- status default PENDING
"""

from sqlalchemy.orm import Session
from app.books.models import Book, BookStatus
from typing import Optional, List


def create_book(
    db: Session,
    title: str,
    author: Optional[str],
    file_name: str,
    file_size: int,
    file_type: str,
    user_id: int
) -> Book:
    """
    Yeni book kaydı oluştur.
    
    Değişiklik: file_path yok artık.
    Status default PENDING (parse bekleniyor).
    """
    db_book = Book(
        title=title,
        author=author,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        user_id=user_id,
        status=BookStatus.PENDING  # Default: parse bekleniyor
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def get_book_by_id(db: Session, book_id: int) -> Optional[Book]:
    """ID ile book bul."""
    return db.query(Book).filter(Book.id == book_id).first()


def get_user_books(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 20
) -> List[Book]:
    """
    User'ın kitaplarını listele (pagination).
    """
    return db.query(Book)\
        .filter(Book.user_id == user_id)\
        .order_by(Book.uploaded_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_user_books_by_status(
    db: Session,
    user_id: int,
    status: BookStatus,
    skip: int = 0,
    limit: int = 20
) -> List[Book]:
    """
    User'ın belirli statusteki kitaplarını listele.
    
    Örnek: Sadece COMPLETED kitapları getir.
    """
    return db.query(Book)\
        .filter(Book.user_id == user_id, Book.status == status)\
        .order_by(Book.uploaded_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()


def count_user_books(db: Session, user_id: int) -> int:
    """User'ın toplam kitap sayısı."""
    return db.query(Book).filter(Book.user_id == user_id).count()


def count_user_books_by_status(db: Session, user_id: int, status: BookStatus) -> int:
    """User'ın belirli statusteki kitap sayısı."""
    return db.query(Book)\
        .filter(Book.user_id == user_id, Book.status == status)\
        .count()


def delete_book(db: Session, book: Book) -> None:
    """
    Book'u sil.
    
    Cascade ile pages de otomatik silinir.
    """
    db.delete(book)
    db.commit()


def search_books(
    db: Session,
    user_id: int,
    query: str,
    skip: int = 0,
    limit: int = 20
) -> List[Book]:
    """
    Kitap ara (title veya author).
    
    ILIKE: Case-insensitive search
    """
    search_pattern = f"%{query}%"
    return db.query(Book)\
        .filter(
            Book.user_id == user_id,
            (Book.title.ilike(search_pattern) | Book.author.ilike(search_pattern))
        )\
        .order_by(Book.uploaded_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
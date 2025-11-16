from sqlalchemy.orm import Session
from app.books.models import Book
from typing import Optional, List


def create_book(
    db: Session,
    title: str,
    author: Optional[str],
    file_path: str,
    file_name: str,
    file_size: int,
    file_type: str,
    user_id: int
) -> Book:
    """Yeni book kaydı oluştur."""
    db_book = Book(
        title=title,
        author=author,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        user_id=user_id
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
    
    Args:
        skip: Kaç tane atla (offset)
        limit: Maksimum kaç tane getir
    """
    return db.query(Book)\
        .filter(Book.user_id == user_id)\
        .order_by(Book.uploaded_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    """
    SQL equivalent:
    SELECT * FROM books 
    WHERE user_id = ? 
    ORDER BY uploaded_at DESC 
    LIMIT ? OFFSET ?
    """


def count_user_books(db: Session, user_id: int) -> int:
    """User'ın toplam kitap sayısı."""
    return db.query(Book).filter(Book.user_id == user_id).count()


def delete_book(db: Session, book: Book) -> None:
    """Book'u sil."""
    db.delete(book)
    db.commit()
"""
BookPage Repository - Database CRUD operations.

BookPage için:
- Sayfa oluşturma (batch)
- Sayfa getirme (tek/çoklu)
- Sayfa silme

Book status güncelleme de burada.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from app.books.models import Book, BookPage, BookStatus


# ============================================
# Book Status Operations
# ============================================

def update_book_status(
    db: Session, 
    book_id: int, 
    status: BookStatus,
    error_message: Optional[str] = None,
    total_pages: Optional[int] = None
) -> Optional[Book]:
    """
    Book status'unu güncelle.
    
    Args:
        db: Database session
        book_id: Book ID
        status: Yeni status
        error_message: Hata mesajı (FAILED için)
        total_pages: Toplam sayfa (COMPLETED için)
    
    Returns:
        Book: Güncellenen book veya None
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None
    
    book.status = status
    
    if error_message is not None:
        book.error_message = error_message
    
    if total_pages is not None:
        book.total_pages = total_pages
    
    db.commit()
    db.refresh(book)
    return book


def set_book_processing(db: Session, book_id: int) -> Optional[Book]:
    """Book'u PROCESSING durumuna geçir."""
    return update_book_status(db, book_id, BookStatus.PROCESSING)


def set_book_completed(db: Session, book_id: int, total_pages: int) -> Optional[Book]:
    """Book'u COMPLETED durumuna geçir."""
    return update_book_status(
        db, book_id, 
        BookStatus.COMPLETED, 
        total_pages=total_pages
    )


def set_book_failed(db: Session, book_id: int, error_message: str) -> Optional[Book]:
    """Book'u FAILED durumuna geçir."""
    return update_book_status(
        db, book_id, 
        BookStatus.FAILED, 
        error_message=error_message
    )


# ============================================
# BookPage Operations
# ============================================

def create_book_pages(
    db: Session,
    book_id: int,
    pages_data: List[dict]
) -> List[BookPage]:
    """
    Birden fazla sayfa oluştur (batch insert).
    
    Args:
        db: Database session
        book_id: Book ID
        pages_data: Sayfa verileri listesi
            [
                {
                    "page_number": 1,
                    "content": "<h1>...</h1><p>...</p>",
                    "word_count": 250,
                    "char_count": 1500
                },
                ...
            ]
    
    Returns:
        List[BookPage]: Oluşturulan sayfalar
    """
    pages = []
    
    for page_data in pages_data:
        page = BookPage(
            book_id=book_id,
            page_number=page_data["page_number"],
            content=page_data["content"],
            word_count=page_data.get("word_count", 0),
            char_count=page_data.get("char_count", 0)
        )
        db.add(page)
        pages.append(page)
    
    db.commit()
    
    # Refresh all pages
    for page in pages:
        db.refresh(page)
    
    return pages


def get_page_by_number(
    db: Session, 
    book_id: int, 
    page_number: int
) -> Optional[BookPage]:
    """
    Belirli sayfa numarasını getir.
    
    Args:
        db: Database session
        book_id: Book ID
        page_number: Sayfa numarası (1'den başlar)
    
    Returns:
        BookPage: Sayfa veya None
    """
    return db.query(BookPage).filter(
        and_(
            BookPage.book_id == book_id,
            BookPage.page_number == page_number
        )
    ).first()


def get_book_pages(
    db: Session,
    book_id: int,
    skip: int = 0,
    limit: int = 10
) -> List[BookPage]:
    """
    Kitabın sayfalarını listele (pagination).
    
    Args:
        db: Database session
        book_id: Book ID
        skip: Atlanacak sayfa (offset)
        limit: Maksimum sayfa sayısı
    
    Returns:
        List[BookPage]: Sayfalar listesi
    """
    return db.query(BookPage)\
        .filter(BookPage.book_id == book_id)\
        .order_by(BookPage.page_number)\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_pages_range(
    db: Session,
    book_id: int,
    start_page: int,
    end_page: int
) -> List[BookPage]:
    """
    Belirli sayfa aralığını getir.
    
    Args:
        db: Database session
        book_id: Book ID
        start_page: Başlangıç sayfa (dahil)
        end_page: Bitiş sayfa (dahil)
    
    Returns:
        List[BookPage]: Sayfalar listesi
    """
    return db.query(BookPage)\
        .filter(
            and_(
                BookPage.book_id == book_id,
                BookPage.page_number >= start_page,
                BookPage.page_number <= end_page
            )
        )\
        .order_by(BookPage.page_number)\
        .all()


def count_book_pages(db: Session, book_id: int) -> int:
    """Kitabın toplam sayfa sayısı."""
    return db.query(BookPage)\
        .filter(BookPage.book_id == book_id)\
        .count()


def delete_book_pages(db: Session, book_id: int) -> int:
    """
    Kitabın tüm sayfalarını sil.
    
    Returns:
        int: Silinen sayfa sayısı
    """
    deleted = db.query(BookPage)\
        .filter(BookPage.book_id == book_id)\
        .delete()
    db.commit()
    return deleted


def get_book_word_count(db: Session, book_id: int) -> int:
    """Kitabın toplam kelime sayısı."""
    from sqlalchemy import func
    result = db.query(func.sum(BookPage.word_count))\
        .filter(BookPage.book_id == book_id)\
        .scalar()
    return result or 0

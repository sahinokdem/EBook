"""
BookBlock Repository - Database CRUD operations.

RAG mimarisi için blok/chunk odaklı veri erişimi sağlar.
Eski page tabanlı fonksiyon isimleri geriye dönük uyumluluk için korunmuştur.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
from types import SimpleNamespace
from app.books.models import Book, BookBlock, BookPage, BookStatus


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

def create_book_blocks(
    db: Session,
    book_id: int,
    blocks_data: List[dict]
) -> List[BookBlock]:
    """
    Birden fazla blok oluştur (batch insert).
    
    Args:
        db: Database session
        book_id: Book ID
        blocks_data: Blok verileri listesi
            [
                {
                    "page_number": 1,
                    "block_index": 0,
                    "content": "...",
                    "word_count": 250,
                    "char_count": 1500,
                    "vector_id": "uuid-or-string"
                },
                ...
            ]
    
    Returns:
        List[BookBlock]: Oluşturulan bloklar
    """
    blocks = []
    
    for block_data in blocks_data:
        block = BookBlock(
            book_id=book_id,
            page_number=block_data["page_number"],
            block_index=block_data.get("block_index", 0),
            content=block_data["content"],
            word_count=block_data.get("word_count", 0),
            char_count=block_data.get("char_count", 0),
            vector_id=block_data.get("vector_id")
        )
        db.add(block)
        blocks.append(block)
    
    db.commit()
    
    for block in blocks:
        db.refresh(block)
    
    return blocks


def create_book_pages(
    db: Session,
    book_id: int,
    pages_data: List[dict]
) -> List[BookPage]:
    """Birden fazla sayfa/blok oluştur (batch insert)."""
    pages = []
    
    for page_data in pages_data:
        page = BookPage(
            book_id=book_id,
            page_number=page_data["page_number"],
            block_index=page_data.get("block_index", 0),  # YENİ EKLENDİ
            vector_id=page_data.get("vector_id"),         # YENİ EKLENDİ
            content=page_data["content"],
            word_count=page_data.get("word_count", 0),
            char_count=page_data.get("char_count", 0)
        )
        db.add(page)
        pages.append(page)
    
    db.commit()
    
    for page in pages:
        db.refresh(page)
    
    return pages


def _aggregate_blocks_to_page_view(book_id: int, page_number: int, blocks: List[BookBlock]):
    """Aynı sayfadaki blokları page-view objesine dönüştür."""
    if not blocks:
        return None
    content = "\n\n".join([block.content for block in blocks if block.content])
    word_count = sum(block.word_count for block in blocks)
    char_count = sum(block.char_count for block in blocks)
    return SimpleNamespace(
        book_id=book_id,
        page_number=page_number,
        content=content,
        word_count=word_count,
        char_count=char_count,
    )


def get_page_by_number(
    db: Session, 
    book_id: int, 
    page_number: int
) -> Optional[SimpleNamespace]:
    """
    Belirli sayfa numarasını getir.
    
    Args:
        db: Database session
        book_id: Book ID
        page_number: Sayfa numarası (1'den başlar)
    
    Returns:
        Page view veya None
    """
    blocks = db.query(BookBlock).filter(
        and_(
            BookBlock.book_id == book_id,
            BookBlock.page_number == page_number
        )
    ).order_by(BookBlock.block_index).all()
    return _aggregate_blocks_to_page_view(book_id, page_number, blocks)


def get_book_pages(
    db: Session,
    book_id: int,
    skip: int = 0,
    limit: int = 10
) -> List[SimpleNamespace]:
    """
    Kitabın sayfalarını listele (pagination).
    
    Args:
        db: Database session
        book_id: Book ID
        skip: Atlanacak sayfa (offset)
        limit: Maksimum sayfa sayısı
    
    Returns:
        List[PageView]: Sayfalar listesi
    """
    page_numbers = db.query(BookBlock.page_number)\
        .filter(BookBlock.book_id == book_id)\
        .group_by(BookBlock.page_number)\
        .order_by(BookBlock.page_number)\
        .offset(skip)\
        .limit(limit)\
        .all()
    result = []
    for (page_number,) in page_numbers:
        blocks = db.query(BookBlock).filter(
            and_(BookBlock.book_id == book_id, BookBlock.page_number == page_number)
        ).order_by(BookBlock.block_index).all()
        page_view = _aggregate_blocks_to_page_view(book_id, page_number, blocks)
        if page_view:
            result.append(page_view)
    return result


def get_pages_range(
    db: Session,
    book_id: int,
    start_page: int,
    end_page: int
) -> List[SimpleNamespace]:
    """
    Belirli sayfa aralığını getir.
    
    Args:
        db: Database session
        book_id: Book ID
        start_page: Başlangıç sayfa (dahil)
        end_page: Bitiş sayfa (dahil)
    
    Returns:
        List[PageView]: Sayfalar listesi
    """
    page_numbers = db.query(BookBlock.page_number)\
        .filter(
            and_(
                BookBlock.book_id == book_id,
                BookBlock.page_number >= start_page,
                BookBlock.page_number <= end_page,
            )
        )\
        .group_by(BookBlock.page_number)\
        .order_by(BookBlock.page_number)\
        .all()
    result = []
    for (page_number,) in page_numbers:
        blocks = db.query(BookBlock).filter(
            and_(BookBlock.book_id == book_id, BookBlock.page_number == page_number)
        ).order_by(BookBlock.block_index).all()
        page_view = _aggregate_blocks_to_page_view(book_id, page_number, blocks)
        if page_view:
            result.append(page_view)
    return result


def count_book_pages(db: Session, book_id: int) -> int:
    """Kitabın toplam benzersiz sayfa sayısı."""
    result = db.query(func.count(func.distinct(BookBlock.page_number)))\
        .filter(BookBlock.book_id == book_id)\
        .scalar()
    return int(result or 0)


def delete_book_blocks(db: Session, book_id: int) -> int:
    """
    Kitabın tüm bloklarını sil.
    
    Returns:
        int: Silinen sayfa sayısı
    """
    deleted = db.query(BookBlock)\
        .filter(BookBlock.book_id == book_id)\
        .delete()
    db.commit()
    return deleted


def delete_book_pages(db: Session, book_id: int) -> int:
    """Geriye dönük uyumluluk alias'ı."""
    return delete_book_blocks(db, book_id)


def get_book_word_count(db: Session, book_id: int) -> int:
    """Kitabın toplam kelime sayısı."""
    result = db.query(func.sum(BookBlock.word_count))\
        .filter(BookBlock.book_id == book_id)\
        .scalar()
    return result or 0


def get_book_blocks(db: Session, book_id: int, limit: int = 200) -> List[BookBlock]:
    """Kitabın bloklarını sırayla getir."""
    return db.query(BookBlock).filter(BookBlock.book_id == book_id)\
        .order_by(BookBlock.page_number, BookBlock.block_index)\
        .limit(limit)\
        .all()

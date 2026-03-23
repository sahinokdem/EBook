"""
Page Service - Business Logic.

Sayfa getirme, kitap durumu kontrol ve okuma işlemleri.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app.books.models import Book, BookBlock, BookStatus
from app.books import repository as book_repository
from app.books import page_repository
from app.books.page_schemas import (
    PageContentResponse,
    PageResponse,
    PageListResponse,
    PageSummaryResponse,
    PagesRangeResponse,
    BookStatusResponse,
    BookStatsResponse
)


def _check_book_access(db: Session, book_id: int, user_id: int) -> Book:
    """
    Kitap erişim kontrolü.
    
    1. Kitap var mı?
    2. User'a ait mi?
    
    Returns:
        Book: Kitap objesi
    
    Raises:
        HTTPException: 404 veya 403
    """
    book = book_repository.get_book_by_id(db, book_id)
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    if book.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this book"
        )
    
    return book


def _check_book_ready(book: Book) -> None:
    """
    Kitabın okunmaya hazır olup olmadığını kontrol et.
    
    Raises:
        HTTPException: Kitap hazır değilse
    """
    if book.status == BookStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book is waiting to be processed"
        )
    
    if book.status == BookStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book is still being processed"
        )
    
    if book.status == BookStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book processing failed: {book.error_message}"
        )


def get_book_status(db: Session, book_id: int, user_id: int) -> BookStatusResponse:
    """
    Kitap durumunu getir.
    
    Args:
        db: Database session
        book_id: Kitap ID
        user_id: Kullanıcı ID
    
    Returns:
        BookStatusResponse: Kitap durumu
    """
    book = _check_book_access(db, book_id, user_id)
    return BookStatusResponse.from_book(book)


def get_page(
    db: Session, 
    book_id: int, 
    page_number: int,
    user_id: int
) -> PageContentResponse:
    """
    Tek sayfa getir (navigation bilgisiyle).
    
    Args:
        db: Database session
        book_id: Kitap ID
        page_number: Sayfa numarası (1'den başlar)
        user_id: Kullanıcı ID
    
    Returns:
        PageContentResponse: Sayfa içeriği + navigation
    """
    # Erişim kontrolü
    book = _check_book_access(db, book_id, user_id)
    _check_book_ready(book)
    
    # Sayfa numarası kontrolü
    if page_number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be at least 1"
        )
    
    if book.total_pages and page_number > book.total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found. Book has {book.total_pages} pages."
        )
    
    # Sayfayı getir
    page = page_repository.get_page_by_number(db, book_id, page_number)
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found"
        )
    
    # Navigation bilgisi
    total_pages = book.total_pages or 0
    has_previous = page_number > 1
    has_next = page_number < total_pages
    
    return PageContentResponse(
        page=PageResponse(
            page_number=page.page_number,
            content=page.content,
            word_count=page.word_count,
            char_count=page.char_count,
            book_id=page.book_id
        ),
        has_previous=has_previous,
        has_next=has_next,
        previous_page=page_number - 1 if has_previous else None,
        next_page=page_number + 1 if has_next else None,
        total_pages=total_pages
    )


def list_pages(
    db: Session,
    book_id: int,
    user_id: int,
    page: int = 1,
    page_size: int = 20
) -> PageListResponse:
    """
    Kitabın sayfalarını listele (pagination, content olmadan).
    
    Sayfa listesi görünümü için - sadece metadata.
    
    Args:
        db: Database session
        book_id: Kitap ID
        user_id: Kullanıcı ID
        page: Sayfa (pagination)
        page_size: Sayfa başına item
    
    Returns:
        PageListResponse: Sayfa listesi
    """
    # Erişim kontrolü
    book = _check_book_access(db, book_id, user_id)
    _check_book_ready(book)
    
    # Pagination
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    
    skip = (page - 1) * page_size
    
    # Sayfaları getir
    pages = page_repository.get_book_pages(db, book_id, skip, page_size)
    
    return PageListResponse(
        pages=[
            PageSummaryResponse(
                page_number=p.page_number,
                word_count=p.word_count,
                char_count=p.char_count
            )
            for p in pages
        ],
        total_pages=book.total_pages or 0,
        current_page=page,
        page_size=page_size,
        book_id=book_id
    )


def get_pages_range(
    db: Session,
    book_id: int,
    user_id: int,
    start_page: int,
    end_page: int
) -> PagesRangeResponse:
    """
    Sayfa aralığı getir.
    
    AI context için birden fazla sayfa içeriği.
    
    Args:
        db: Database session
        book_id: Kitap ID
        user_id: Kullanıcı ID
        start_page: Başlangıç sayfa (dahil)
        end_page: Bitiş sayfa (dahil)
    
    Returns:
        PagesRangeResponse: Sayfalar listesi
    """
    # Erişim kontrolü
    book = _check_book_access(db, book_id, user_id)
    _check_book_ready(book)
    
    # Validation
    if start_page < 1:
        start_page = 1
    if end_page < start_page:
        end_page = start_page
    
    # Maksimum 20 sayfa (context limit)
    if end_page - start_page > 20:
        end_page = start_page + 20
    
    total_pages = book.total_pages or 0
    if end_page > total_pages:
        end_page = total_pages
    
    # Sayfaları getir
    pages = page_repository.get_pages_range(db, book_id, start_page, end_page)
    
    return PagesRangeResponse(
        pages=[
            PageResponse(
                page_number=p.page_number,
                content=p.content,
                word_count=p.word_count,
                char_count=p.char_count,
                book_id=p.book_id
            )
            for p in pages
        ],
        start_page=start_page,
        end_page=end_page,
        total_pages=total_pages,
        book_id=book_id
    )


def get_book_stats(db: Session, book_id: int, user_id: int) -> BookStatsResponse:
    """
    Kitap istatistiklerini getir.
    
    Args:
        db: Database session
        book_id: Kitap ID
        user_id: Kullanıcı ID
    
    Returns:
        BookStatsResponse: Kitap istatistikleri
    """
    # Erişim kontrolü
    book = _check_book_access(db, book_id, user_id)
    _check_book_ready(book)
    
    # İstatistikleri hesapla
    total_words = page_repository.get_book_word_count(db, book_id)
    
    # Karakter sayısı için tüm sayfaları al (veya ayrı query)
    pages = page_repository.get_book_pages(db, book_id, skip=0, limit=10000)
    total_chars = sum(p.char_count for p in pages)
    
    # Okuma süresi hesapla
    reading_time = BookStatsResponse.calculate_reading_time(total_words)
    
    return BookStatsResponse(
        book_id=book_id,
        total_pages=book.total_pages or 0,
        total_words=total_words,
        total_chars=total_chars,
        estimated_reading_time=reading_time
    )

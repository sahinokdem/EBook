"""
Book Service - Updated.

Değişiklikler:
- PDF saklanmıyor, sadece parse ediliyor
- Upload sonrası Celery task tetikleniyor
- Sync processing opsiyonu (development için)
"""

import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from app.books import repository
from app.books.schemas import BookCreate, BookListResponse
from app.books.models import Book, BookStatus
from app.core.config import settings


# Celery kullanılacak mı? (Development'ta False olabilir)
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"


def upload_book(
    db: Session,
    file: UploadFile,
    book_data: BookCreate,
    user_id: int
) -> Book:
    """
    Book upload - File validation + Parse işlemi başlat.
    
    Değişiklik: PDF artık saklanmıyor!
    
    Steps:
    1. File validation (size, type)
    2. Create DB record (status: PENDING)
    3. Parse PDF (sync veya async)
    4. Return book
    
    Args:
        db: Database session
        file: Uploaded file
        book_data: Book metadata (title, author)
        user_id: User ID
    
    Returns:
        Book: Created book (status: PENDING veya COMPLETED)
    """
    
    # 1. File validation
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    allowed_types = ["application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF allowed."
        )
    
    # 2. File içeriğini oku (memory'de)
    file_content = file.file.read()
    
    # 3. DB record oluştur (PENDING status)
    new_book = repository.create_book(
        db=db,
        title=book_data.title,
        author=book_data.author,
        file_name=file.filename,
        file_size=file.size,
        file_type=file.content_type,
        user_id=user_id
    )
    
    # 4. PDF processing başlat
    if USE_CELERY:
        # Async processing (production)
        from app.books.book_tasks import start_book_processing
        task_id = start_book_processing(new_book.id, file_content)
        # Task ID'yi saklamak istersen book modeline ekleyebilirsin
    else:
        # Sync processing (development)
        from app.books.book_tasks import process_book_sync
        result = process_book_sync(new_book.id, file_content, db)
        
        # Refresh book (status güncellenmiş olabilir)
        db.refresh(new_book)
    
    return new_book


def get_book(db: Session, book_id: int, user_id: int) -> Book:
    """
    Get book by ID.
    
    Authorization: User can only access their own books.
    """
    book = repository.get_book_by_id(db, book_id)
    
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


def list_user_books(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20
) -> BookListResponse:
    """
    List user's books with pagination.
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    
    skip = (page - 1) * page_size
    
    books = repository.get_user_books(db, user_id, skip, page_size)
    total = repository.count_user_books(db, user_id)
    
    return BookListResponse(
        books=books,
        total=total,
        page=page,
        page_size=page_size
    )


def delete_book(db: Session, book_id: int, user_id: int) -> None:
    """
    Delete book.
    
    Değişiklik: File deletion yok artık (PDF saklanmıyor).
    Cascade ile pages otomatik silinecek.
    """
    book = repository.get_book_by_id(db, book_id)
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    if book.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this book"
        )
    
    # Delete DB record (cascade ile pages da silinir)
    repository.delete_book(db, book)


def retry_processing(db: Session, book_id: int, user_id: int) -> Book:
    """
    Failed olan kitabı tekrar işle.
    
    Kullanım: Kitap FAILED durumundaysa tekrar denenebilir.
    NOT: Bunun için original file lazım - şu anki tasarımda mümkün değil.
    
    İleride: Temporary storage eklenebilir.
    """
    book = get_book(db, book_id, user_id)
    
    if book.status != BookStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed books can be retried"
        )
    
    # Original file olmadığı için retry yapılamaz
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot retry - original file not stored. Please upload again."
    )
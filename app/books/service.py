import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from app.books import repository
from app.books.schemas import BookCreate, BookListResponse
from app.books.models import Book
from app.core.config import settings


def upload_book(
    db: Session,
    file: UploadFile,
    book_data: BookCreate,
    user_id: int
) -> Book:
    """
    Book upload - File save + DB record.
    
    Steps:
    1. File validation (size, type)
    2. Create user upload directory
    3. Save file to disk
    4. Create DB record
    """
    
    # 1. File validation
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Allowed file types (şimdilik sadece PDF ve EPUB)
    allowed_types = ["application/pdf", "application/epub+zip"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PDF, EPUB"
        )
    
    # 2. Create upload directory
    user_upload_dir = Path(settings.UPLOAD_DIR) / f"user_{user_id}"
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    
    """
    Directory structure:
    uploads/
    ├── user_1/
    │   ├── book_1.pdf
    │   └── book_2.epub
    └── user_2/
        └── book_3.pdf
    """
    
    # 3. Save file
    file_path = user_upload_dir / file.filename
    
    # File already exists? Add timestamp
    if file_path.exists():
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = file_path.stem
        file_suffix = file_path.suffix
        file_path = user_upload_dir / f"{file_stem}_{timestamp}{file_suffix}"
    
    # Write file to disk
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    """
    shutil.copyfileobj():
    - Efficient file copy (chunks)
    - Memory-friendly (büyük dosyalar için)
    """
    
    # 4. Create DB record
    new_book = repository.create_book(
        db=db,
        title=book_data.title,
        author=book_data.author,
        file_path=str(file_path),
        file_name=file.filename,
        file_size=file.size,
        file_type=file.content_type,
        user_id=user_id
    )
    
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
    
    # Authorization check
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
    # Validation
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
    
    Steps:
    1. Find book
    2. Authorization check
    3. Delete file from disk
    4. Delete DB record
    """
    book = repository.get_book_by_id(db, book_id)
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Authorization check
    if book.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this book"
        )
    
    # Delete file from disk
    file_path = Path(book.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete DB record
    repository.delete_book(db, book)
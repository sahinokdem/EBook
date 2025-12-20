from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.shared.dependencies import get_db, get_current_user
from app.books.schemas import BookResponse, BookListResponse
from app.users.models import User
from app.books import service


router = APIRouter()


@router.post("/upload", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new book.
    
    Protected endpoint - JWT required.
    
    Multipart form data:
    - file: Book file (PDF, EPUB)
    - title: Book title
    - author: Book author (optional)
    
    Supported formats:
    - PDF (application/pdf)
    - EPUB (application/epub+zip)
    
    Response (201 Created):
    ```json
    {
        "id": 1,
        "title": "Harry Potter",
        "author": "J.K. Rowling",
        "file_name": "harry_potter.epub",
        "file_size": 5242880,
        "file_type": "application/epub+zip",
        "user_id": 1,
        "uploaded_at": "2024-11-15T19:30:00Z"
    }
    ```
    """
    
    """
    File upload parameters:
    - UploadFile: FastAPI's file upload type
    - File(...): Required file
    - Form(...): Form field (multipart/form-data)
    
    Multipart form'da JSON gönderemezsin, Form() kullanmalısın.
    """
    
    from app.books.schemas import BookCreate
    book_data = BookCreate(title=title, author=author)
    
    new_book = service.upload_book(db, file, book_data, current_user.id)
    return new_book


@router.get("", response_model=BookListResponse)
def list_books(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List current user's books with pagination.
    
    Protected endpoint - JWT required.
    
    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    
    Response (200 OK):
    ```json
    {
        "books": [...],
        "total": 10,
        "page": 1,
        "page_size": 20
    }
    ```
    """
    return service.list_user_books(db, current_user.id, page, page_size)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single book details.
    
    Protected endpoint - JWT required.
    Authorization: User can only access their own books.
    
    Response (200 OK): BookResponse
    
    Errors:
    - 404: Book not found
    - 403: Not authorized
    """
    return service.get_book(db, book_id, current_user.id)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a book.
    
    Protected endpoint - JWT required.
    Authorization: User can only delete their own books.
    
    Response (204 No Content): Empty body
    
    Errors:
    - 404: Book not found
    - 403: Not authorized
    """
    service.delete_book(db, book_id, current_user.id)
    return None
    
    """
    204 No Content:
    - Başarılı deletion için standart
    - Response body yok
    """


"""
Router Summary:

All endpoints protected (JWT required):
- POST /upload       → Book upload
- GET /              → List user's books (pagination)
- GET /{book_id}     → Get single book
- DELETE /{book_id}  → Delete book

main.py'de:
    app.include_router(
        books_router,
        prefix="/api/v1/books",
        tags=["Books"]
    )
"""
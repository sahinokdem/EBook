"""
Page Router - API Endpoints.

Sayfa okuma ve kitap durumu endpointleri.

Endpoints:
- GET /books/{book_id}/status     → Kitap işleme durumu
- GET /books/{book_id}/pages      → Sayfa listesi
- GET /books/{book_id}/pages/{n}  → Tek sayfa içeriği
- GET /books/{book_id}/pages/range → Sayfa aralığı
- GET /books/{book_id}/stats      → Kitap istatistikleri
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.shared.dependencies import get_db, get_current_user
from app.users.models import User
from app.books import page_service
from app.books.page_schemas import (
    PageContentResponse,
    PageListResponse,
    PagesRangeResponse,
    BookStatusResponse,
    BookStatsResponse
)


router = APIRouter()


@router.get("/{book_id}/status", response_model=BookStatusResponse)
def get_book_status(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get book processing status.
    
    Protected endpoint - JWT required.
    
    Bu endpoint'i kullanarak:
    - Upload sonrası kitabın hazır olup olmadığını kontrol edebilirsiniz
    - Processing durumunda polling yapabilirsiniz
    
    Response (200 OK):
    ```json
    {
        "book_id": 1,
        "status": "completed",
        "total_pages": 320,
        "error_message": null,
        "progress_message": "Ready to read!"
    }
    ```
    
    Status değerleri:
    - "pending": Henüz işlenmedi
    - "processing": İşleniyor
    - "completed": Hazır
    - "failed": Hata oluştu
    """
    return page_service.get_book_status(db, book_id, current_user.id)


@router.get("/{book_id}/pages", response_model=PageListResponse)
def list_pages(
    book_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List book pages (without content).
    
    Protected endpoint - JWT required.
    
    Sayfa listesi görünümü için - sadece metadata.
    Content almak için /pages/{page_number} kullanın.
    
    Query params:
    - page: Pagination sayfa numarası (default: 1)
    - page_size: Sayfa başına item (default: 20, max: 100)
    
    Response (200 OK):
    ```json
    {
        "pages": [
            {"page_number": 1, "word_count": 350, "char_count": 2100},
            {"page_number": 2, "word_count": 420, "char_count": 2500},
            ...
        ],
        "total_pages": 320,
        "current_page": 1,
        "page_size": 20,
        "book_id": 1
    }
    ```
    
    Errors:
    - 404: Book not found
    - 403: Not authorized
    - 400: Book not ready (pending/processing/failed)
    """
    return page_service.list_pages(db, book_id, current_user.id, page, page_size)


@router.get("/{book_id}/pages/range", response_model=PagesRangeResponse)
def get_pages_range(
    book_id: int,
    start: int = Query(..., ge=1, description="Start page (inclusive)"),
    end: int = Query(..., ge=1, description="End page (inclusive)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get multiple pages content.
    
    Protected endpoint - JWT required.
    
    Birden fazla sayfa içeriği almak için.
    AI context oluşturmak için kullanışlı.
    
    Maksimum 20 sayfa alınabilir (context limit).
    
    Query params:
    - start: Başlangıç sayfa (dahil)
    - end: Bitiş sayfa (dahil)
    
    Example: /books/1/pages/range?start=5&end=10
    
    Response (200 OK):
    ```json
    {
        "pages": [
            {
                "page_number": 5,
                "content": "<h1>...</h1><p>...</p>",
                "word_count": 350,
                "char_count": 2100,
                "book_id": 1
            },
            ...
        ],
        "start_page": 5,
        "end_page": 10,
        "total_pages": 320,
        "book_id": 1
    }
    ```
    
    Errors:
    - 404: Book not found
    - 403: Not authorized
    - 400: Book not ready
    """
    return page_service.get_pages_range(db, book_id, current_user.id, start, end)


@router.get("/{book_id}/pages/{page_number}", response_model=PageContentResponse)
def get_page(
    book_id: int,
    page_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single page content.
    
    Protected endpoint - JWT required.
    
    Tek sayfa içeriği + navigation bilgisi.
    
    Path params:
    - book_id: Kitap ID
    - page_number: Sayfa numarası (1'den başlar)
    
    Response (200 OK):
    ```json
    {
        "page": {
            "page_number": 5,
            "content": "<h1>Chapter 2</h1><p>The story continues...</p>",
            "word_count": 350,
            "char_count": 2100,
            "book_id": 1
        },
        "has_previous": true,
        "has_next": true,
        "previous_page": 4,
        "next_page": 6,
        "total_pages": 320
    }
    ```
    
    Content HTML formatındadır:
    - <h1>, <h2>, <h3>: Başlıklar
    - <p>: Paragraflar
    - <strong>: Kalın metin
    - <em>: İtalik metin
    
    Errors:
    - 404: Book or page not found
    - 403: Not authorized
    - 400: Book not ready (pending/processing/failed)
    """
    return page_service.get_page(db, book_id, page_number, current_user.id)


@router.get("/{book_id}/stats", response_model=BookStatsResponse)
def get_book_stats(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get book statistics.
    
    Protected endpoint - JWT required.
    
    Kitap istatistikleri:
    - Toplam sayfa
    - Toplam kelime
    - Tahmini okuma süresi
    
    Response (200 OK):
    ```json
    {
        "book_id": 1,
        "total_pages": 320,
        "total_words": 85000,
        "total_chars": 450000,
        "estimated_reading_time": "5h 40m"
    }
    ```
    
    Errors:
    - 404: Book not found
    - 403: Not authorized
    - 400: Book not ready
    """
    return page_service.get_book_stats(db, book_id, current_user.id)


"""
Router Summary:

All endpoints protected (JWT required):

Status & Info:
- GET /{book_id}/status  → Processing durumu
- GET /{book_id}/stats   → Kitap istatistikleri

Page Reading:
- GET /{book_id}/pages           → Sayfa listesi (metadata)
- GET /{book_id}/pages/{n}       → Tek sayfa içeriği
- GET /{book_id}/pages/range     → Sayfa aralığı

main.py'de:
    app.include_router(
        page_router,
        prefix="/api/v1/books",
        tags=["Book Pages"]
    )

Örnek flow:
1. POST /books/upload → Kitap upload et
2. GET /books/{id}/status → Durumu kontrol et (polling)
3. status == "completed" → Hazır!
4. GET /books/{id}/pages/1 → İlk sayfayı oku
5. GET /books/{id}/pages/2 → Sonraki sayfa...
"""

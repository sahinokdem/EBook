"""
BookPage Schemas - Request/Response modelleri.

Sayfa içeriği ve kitap durumu için Pydantic modelleri.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum


# ============================================
# Enums
# ============================================

class BookStatusEnum(str, Enum):
    """Book processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================
# Book Schemas (Updated)
# ============================================

class BookBase(BaseModel):
    """Base schema - Ortak fieldlar."""
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=255)


class BookCreate(BookBase):
    """Book upload request - sadece metadata."""
    pass


class BookResponse(BookBase):
    """
    Book response schema (güncellendi).
    
    Response:
    {
        "id": 1,
        "title": "Harry Potter",
        "author": "J.K. Rowling",
        "file_name": "harry_potter.pdf",
        "file_size": 5242880,
        "file_type": "application/pdf",
        "status": "completed",
        "total_pages": 320,
        "user_id": 1,
        "uploaded_at": "2024-11-15T19:30:00Z"
    }
    """
    id: int
    file_name: str
    file_size: int
    file_type: str
    status: BookStatusEnum
    total_pages: Optional[int] = None
    error_message: Optional[str] = None
    user_id: int
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BookListResponse(BaseModel):
    """Book list response - Pagination için."""
    books: List[BookResponse]
    total: int
    page: int = 1
    page_size: int = 20


class BookStatusResponse(BaseModel):
    """
    Book status response - Processing durumu.
    
    Response:
    {
        "book_id": 1,
        "status": "processing",
        "total_pages": null,
        "error_message": null,
        "progress_message": "Processing..."
    }
    """
    book_id: int
    status: BookStatusEnum
    total_pages: Optional[int] = None
    error_message: Optional[str] = None
    progress_message: str
    
    @classmethod
    def from_book(cls, book) -> "BookStatusResponse":
        """Book modelinden oluştur."""
        messages = {
            BookStatusEnum.PENDING: "Waiting to be processed...",
            BookStatusEnum.PROCESSING: "Processing PDF...",
            BookStatusEnum.COMPLETED: "Ready to read!",
            BookStatusEnum.FAILED: "Processing failed"
        }
        
        return cls(
            book_id=book.id,
            status=book.status,
            total_pages=book.total_pages,
            error_message=book.error_message,
            progress_message=messages.get(book.status, "Unknown")
        )


# ============================================
# Page Schemas
# ============================================

class PageResponse(BaseModel):
    """
    Tek sayfa response.
    
    Response:
    {
        "page_number": 1,
        "content": "<h1>Chapter 1</h1><p>Once upon a time...</p>",
        "word_count": 350,
        "char_count": 2100,
        "book_id": 1
    }
    """
    page_number: int
    content: str
    word_count: int
    char_count: int
    book_id: int
    
    model_config = ConfigDict(from_attributes=True)


class PageSummaryResponse(BaseModel):
    """
    Sayfa özeti (content olmadan).
    
    Liste görünümü için - content yüklemeden sayfa bilgisi.
    """
    page_number: int
    word_count: int
    char_count: int
    
    model_config = ConfigDict(from_attributes=True)


class PageListResponse(BaseModel):
    """
    Sayfa listesi response.
    
    Response:
    {
        "pages": [...],
        "total_pages": 320,
        "current_page": 1,
        "page_size": 10,
        "book_id": 1
    }
    """
    pages: List[PageSummaryResponse]
    total_pages: int
    current_page: int  # Pagination current page
    page_size: int
    book_id: int


class PageContentResponse(BaseModel):
    """
    Sayfa içeriği response (navigation ile).
    
    Response:
    {
        "page": {...},
        "has_previous": false,
        "has_next": true,
        "previous_page": null,
        "next_page": 2,
        "total_pages": 320
    }
    """
    page: PageResponse
    has_previous: bool
    has_next: bool
    previous_page: Optional[int]
    next_page: Optional[int]
    total_pages: int


class PagesRangeResponse(BaseModel):
    """
    Sayfa aralığı response.
    
    Birden fazla sayfa içeriği (örn: AI context için).
    
    Response:
    {
        "pages": [...],
        "start_page": 5,
        "end_page": 10,
        "total_pages": 320,
        "book_id": 1
    }
    """
    pages: List[PageResponse]
    start_page: int
    end_page: int
    total_pages: int
    book_id: int


# ============================================
# Book Reading Progress (ileride kullanılabilir)
# ============================================

class ReadingProgressResponse(BaseModel):
    """
    Okuma ilerlemesi (ileride).
    
    Response:
    {
        "book_id": 1,
        "current_page": 45,
        "total_pages": 320,
        "progress_percent": 14.1,
        "estimated_time_left": "5h 30m"
    }
    """
    book_id: int
    current_page: int
    total_pages: int
    progress_percent: float
    estimated_time_left: Optional[str] = None


# ============================================
# Book Stats
# ============================================

class BookStatsResponse(BaseModel):
    """
    Kitap istatistikleri.
    
    Response:
    {
        "book_id": 1,
        "total_pages": 320,
        "total_words": 85000,
        "total_chars": 450000,
        "estimated_reading_time": "5h 40m"
    }
    """
    book_id: int
    total_pages: int
    total_words: int
    total_chars: int
    estimated_reading_time: str
    
    @classmethod
    def calculate_reading_time(cls, word_count: int, wpm: int = 250) -> str:
        """
        Okuma süresini hesapla.
        
        Args:
            word_count: Toplam kelime sayısı
            wpm: Words per minute (ortalama 250)
        
        Returns:
            str: "Xh Ym" formatında süre
        """
        minutes = word_count / wpm
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class BookBase(BaseModel):
    """Base schema - Ortak fieldlar."""
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=255)


class BookCreate(BookBase):
    """
    Book upload request metadata.
    
    File upload multipart/form-data olarak gelir:
    - File: UploadFile
    - Metadata: BookCreate (form fields)
    """
    pass
    
    """
    Şimdilik sadece title ve author.
    File bilgileri (file_path, file_size, etc.) otomatik set edilecek.
    """


class BookResponse(BookBase):
    """
    Book response schema.
    
    Response:
    {
        "id": 1,
        "title": "Harry Potter",
        "author": "J.K. Rowling",
        "file_name": "harry_potter.pdf",
        "file_size": 5242880,
        "file_type": "application/pdf",
        "uploaded_at": "2024-11-15T19:30:00Z"
    }
    """
    id: int
    file_name: str
    file_size: int
    file_type: str
    user_id: int
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BookListResponse(BaseModel):
    """
    Book list response - Pagination için.
    
    Response:
    {
        "books": [...],
        "total": 10,
        "page": 1,
        "page_size": 20
    }
    """
    books: list[BookResponse]
    total: int
    page: int = 1
    page_size: int = 20
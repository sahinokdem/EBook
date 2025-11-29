"""
Celery Tasks - Asenkron PDF işleme.

PDF parse işlemi uzun sürebilir (büyük dosyalar için).
Celery ile background'da çalıştırıyoruz.

Kurulum:
    pip install celery redis

Redis başlatma:
    docker run -d -p 6379:6379 redis

Celery worker başlatma:
    celery -A app.tasks.celery_app worker --loglevel=info

Kullanım:
    from app.tasks.book_tasks import process_book_task
    
    # Task'ı async başlat
    task = process_book_task.delay(book_id, file_content_base64)
    
    # Task durumunu kontrol et
    result = task.AsyncResult(task.id)
    print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE
"""

from celery import Celery
from typing import Optional
import base64
import os

from app.core.config import settings


# ============================================
# Celery Configuration
# ============================================

# Redis URL (default: localhost:6379)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Celery app oluştur
celery_app = Celery(
    "book_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Task sonuçları 1 saat sakla
    result_expires=3600,
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


# ============================================
# Book Processing Task
# ============================================

@celery_app.task(bind=True, max_retries=3)
def process_book_task(self, book_id: int, file_content_base64: str) -> dict:
    """
    PDF'i parse et ve sayfaları DB'ye kaydet.
    
    Celery task - background'da çalışır.
    
    Args:
        book_id: Book ID
        file_content_base64: PDF içeriği (base64 encoded)
    
    Returns:
        dict: İşlem sonucu
            {
                "success": True,
                "book_id": 1,
                "total_pages": 150,
                "message": "Successfully processed"
            }
    
    Raises:
        Retry: İşlem başarısız olursa retry
    """
    from app.shared.database import SessionLocal
    from app.books.pdf_parser import pdf_parser
    from app.books import page_repository
    
    # Database session
    db = SessionLocal()
    
    try:
        # 1. Book'u PROCESSING durumuna al
        page_repository.set_book_processing(db, book_id)
        
        # 2. Base64'ten bytes'a çevir
        file_content = base64.b64decode(file_content_base64)
        
        # 3. PDF'i parse et
        result = pdf_parser.parse_file(file_content)
        
        if not result.success:
            # Parse başarısız
            page_repository.set_book_failed(db, book_id, result.error_message)
            return {
                "success": False,
                "book_id": book_id,
                "error": result.error_message
            }
        
        # 4. Sayfaları DB'ye kaydet
        pages_data = [
            {
                "page_number": page.page_number,
                "content": page.content,
                "word_count": page.word_count,
                "char_count": page.char_count
            }
            for page in result.pages
        ]
        
        page_repository.create_book_pages(db, book_id, pages_data)
        
        # 5. Book'u COMPLETED durumuna al
        page_repository.set_book_completed(db, book_id, result.total_pages)
        
        return {
            "success": True,
            "book_id": book_id,
            "total_pages": result.total_pages,
            "message": f"Successfully processed {result.total_pages} pages"
        }
        
    except Exception as e:
        # Hata durumunda
        error_msg = str(e)
        
        try:
            page_repository.set_book_failed(db, book_id, error_msg)
        except:
            pass
        
        # Retry (max 3 kez)
        raise self.retry(exc=e, countdown=60)  # 60 saniye sonra tekrar dene
        
    finally:
        db.close()


# ============================================
# Helper Functions
# ============================================

def start_book_processing(book_id: int, file_content: bytes) -> str:
    """
    Book processing task'ını başlat.
    
    Args:
        book_id: Book ID
        file_content: PDF içeriği (bytes)
    
    Returns:
        str: Celery task ID
    """
    # Bytes'ı base64'e çevir (JSON serialization için)
    file_content_base64 = base64.b64encode(file_content).decode('utf-8')
    
    # Task'ı başlat
    task = process_book_task.delay(book_id, file_content_base64)
    
    return task.id


def get_task_status(task_id: str) -> dict:
    """
    Task durumunu kontrol et.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        dict: Task durumu
            {
                "task_id": "abc123",
                "status": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE",
                "result": {...}  # SUCCESS durumunda
                "error": "..."   # FAILURE durumunda
            }
    """
    result = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": result.status
    }
    
    if result.successful():
        response["result"] = result.result
    elif result.failed():
        response["error"] = str(result.result)
    
    return response


# ============================================
# Sync Processing (Celery olmadan test için)
# ============================================

def process_book_sync(book_id: int, file_content: bytes, db) -> dict:
    """
    PDF'i senkron olarak işle (test için).
    
    Celery kurulu değilse veya development ortamında kullanılabilir.
    
    Args:
        book_id: Book ID
        file_content: PDF içeriği
        db: Database session
    
    Returns:
        dict: İşlem sonucu
    """
    from app.books.pdf_parser import pdf_parser
    from app.books import page_repository
    
    try:
        # 1. Book'u PROCESSING durumuna al
        page_repository.set_book_processing(db, book_id)
        
        # 2. PDF'i parse et
        result = pdf_parser.parse_file(file_content)
        
        if not result.success:
            page_repository.set_book_failed(db, book_id, result.error_message)
            return {
                "success": False,
                "book_id": book_id,
                "error": result.error_message
            }
        
        # 3. Sayfaları DB'ye kaydet
        pages_data = [
            {
                "page_number": page.page_number,
                "content": page.content,
                "word_count": page.word_count,
                "char_count": page.char_count
            }
            for page in result.pages
        ]
        
        page_repository.create_book_pages(db, book_id, pages_data)
        
        # 4. Book'u COMPLETED durumuna al
        page_repository.set_book_completed(db, book_id, result.total_pages)
        
        return {
            "success": True,
            "book_id": book_id,
            "total_pages": result.total_pages,
            "message": f"Successfully processed {result.total_pages} pages"
        }
        
    except Exception as e:
        error_msg = str(e)
        page_repository.set_book_failed(db, book_id, error_msg)
        return {
            "success": False,
            "book_id": book_id,
            "error": error_msg
        }

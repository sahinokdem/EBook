# 📚 Book Pages Feature - Implementation Guide

PDF upload sonrası sayfa sayfa okuma özelliği.

## 📁 Dosya Yapısı

```
app/
├── books/
│   ├── models.py           ← GÜNCELLENDİ (Book + BookPage)
│   ├── repository.py       ← GÜNCELLENDİ (file_path kaldırıldı)
│   ├── service.py          ← GÜNCELLENDİ (PDF processing)
│   ├── router.py           ← Mevcut (değişiklik yok)
│   ├── schemas.py          ← GÜNCELLENDİ (status eklendi)
│   ├── pdf_parser.py       ← YENİ (PDF → HTML)
│   ├── page_repository.py  ← YENİ (BookPage CRUD)
│   ├── page_service.py     ← YENİ (Page business logic)
│   ├── page_router.py      ← YENİ (Page endpoints)
│   └── page_schemas.py     ← YENİ (Page response models)
├── tasks/
│   └── book_tasks.py       ← YENİ (Celery tasks)
├── core/
│   └── config.py           ← GÜNCELLENDİ (Celery config)
└── migrations/
    └── xxxx_add_book_pages.py  ← YENİ (Alembic migration)
```

## 🔄 Değişiklikler Özeti

### Book Model (models.py)
```python
# Kaldırılan
- file_path  # PDF artık saklanmıyor

# Eklenen
+ status: BookStatus (pending/processing/completed/failed)
+ total_pages: int
+ error_message: str
+ pages: relationship → BookPage
```

### Yeni Model: BookPage
```python
class BookPage:
    id: int
    book_id: int (FK)
    page_number: int
    content: str (HTML)
    word_count: int
    char_count: int
```

## 🚀 Kurulum

### 1. Dependencies
```bash
pip install PyMuPDF celery redis
```

### 2. Redis (Celery için)
```bash
# Docker ile
docker run -d -p 6379:6379 redis

# veya brew (macOS)
brew install redis && brew services start redis
```

### 3. Environment Variables (.env)
```env
# Mevcut ayarlar...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
USE_CELERY=false  # Development'ta false, production'da true
```

### 4. Migration
```bash
alembic revision --autogenerate -m "add book pages"
alembic upgrade head
```

### 5. Celery Worker (Production)
```bash
celery -A app.tasks.book_tasks.celery_app worker --loglevel=info
```

## 📡 API Endpoints

### Mevcut (Books)
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/v1/books/upload` | Kitap upload |
| GET | `/api/v1/books` | Kitap listesi |
| GET | `/api/v1/books/{id}` | Kitap detay |
| DELETE | `/api/v1/books/{id}` | Kitap sil |

### Yeni (Pages)
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/books/{id}/status` | İşleme durumu |
| GET | `/api/v1/books/{id}/pages` | Sayfa listesi |
| GET | `/api/v1/books/{id}/pages/{n}` | Sayfa içeriği |
| GET | `/api/v1/books/{id}/pages/range` | Sayfa aralığı |
| GET | `/api/v1/books/{id}/stats` | Kitap istatistikleri |

## 🔄 Upload → Read Flow

```
1. Client: POST /books/upload (PDF file)
   ↓
2. Server: 
   - File validation
   - Create Book (status: PENDING)
   - Start processing (sync/async)
   ↓
3. Processing:
   - PDF → HTML parse
   - Create BookPages
   - Update Book (status: COMPLETED)
   ↓
4. Client: GET /books/{id}/status
   - Poll until status == "completed"
   ↓
5. Client: GET /books/{id}/pages/1
   - Read first page
```

## 📖 Response Examples

### Book Status
```json
GET /api/v1/books/1/status

{
  "book_id": 1,
  "status": "completed",
  "total_pages": 320,
  "error_message": null,
  "progress_message": "Ready to read!"
}
```

### Page Content
```json
GET /api/v1/books/1/pages/5

{
  "page": {
    "page_number": 5,
    "content": "<h1>Chapter 2</h1><p>The story <strong>continues</strong>...</p>",
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

### Page Range (AI Context)
```json
GET /api/v1/books/1/pages/range?start=5&end=10

{
  "pages": [
    {"page_number": 5, "content": "...", ...},
    {"page_number": 6, "content": "...", ...},
    ...
  ],
  "start_page": 5,
  "end_page": 10,
  "total_pages": 320,
  "book_id": 1
}
```

## 🎨 HTML Content Format

PDF'den çıkarılan içerik HTML formatında:

```html
<h1>Chapter Title</h1>
<h2>Section Title</h2>
<p>Normal paragraph text here.</p>
<p>Text with <strong>bold</strong> and <em>italic</em> formatting.</p>
```

### Supported Tags
- `<h1>`, `<h2>`, `<h3>` - Başlıklar (font size'a göre)
- `<p>` - Paragraflar
- `<strong>` - Kalın metin
- `<em>` - İtalik metin

## ⚙️ Configuration

### PDF Parser (pdf_parser.py)
```python
H1_MIN_SIZE = 18  # 18pt+ → <h1>
H2_MIN_SIZE = 14  # 14-17pt → <h2>
H3_MIN_SIZE = 12  # 12-13pt → <h3>
# Geri kalan → <p>
```

### Processing Mode
```python
# config.py veya .env
USE_CELERY = False  # Sync processing (development)
USE_CELERY = True   # Async processing (production)
```

## 🧪 Testing

```python
# Test upload
response = client.post(
    "/api/v1/books/upload",
    files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    data={"title": "Test Book", "author": "Test Author"},
    headers={"Authorization": f"Bearer {token}"}
)

book_id = response.json()["id"]

# Poll status
while True:
    status = client.get(f"/api/v1/books/{book_id}/status", ...)
    if status.json()["status"] == "completed":
        break
    time.sleep(1)

# Read page
page = client.get(f"/api/v1/books/{book_id}/pages/1", ...)
print(page.json()["page"]["content"])
```

## 📝 main.py Entegrasyonu

```python
from fastapi import FastAPI
from app.books.router import router as books_router
from app.books.page_router import router as pages_router

app = FastAPI()

# Books endpoints
app.include_router(
    books_router,
    prefix="/api/v1/books",
    tags=["Books"]
)

# Pages endpoints (aynı prefix, farklı router)
app.include_router(
    pages_router,
    prefix="/api/v1/books",
    tags=["Book Pages"]
)
```

## 🔮 Gelecek Geliştirmeler

1. **Reading Progress** - Kullanıcının nerede kaldığını kaydet
2. **Bookmarks** - Sayfa işaretleme
3. **EPUB Support** - EPUB dosyaları için parser
4. **Search** - Kitap içinde arama
5. **AI Integration** - Sayfa içeriğini AI'a context olarak gönder

## ⚠️ Önemli Notlar

1. **PDF Saklanmıyor**: Upload sonrası PDF silinir, sadece parse edilmiş içerik kalır
2. **Retry Yok**: Failed kitap için tekrar upload gerekli
3. **Max Pages**: 1000 sayfa limiti (config'den değiştirilebilir)
4. **Max Range**: `/pages/range` endpoint'i max 20 sayfa döner
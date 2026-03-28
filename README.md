# 📚 AI-Powered eBook Backend (FastAPI)

Bu proje, kullanıcıların PDF/EPUB kitaplarını yükleyip **okuyabildiği, çevirebildiği, özetleyebildiği ve kitapla doğal dilde soru-cevap yapabildiği** bir backend sistemidir.

> Kısaca: Klasik “dosya yükle ve görüntüle” yaklaşımını, **RAG + LLM + cache** ile ölçeklenebilir bir ürün mimarisine dönüştürüyorum.

---

## 🚀 Neden Bu Proje Önemli?

Çoğu eBook backend’i sadece dosyayı saklar. Bu projede amaç:

- Kitabı sadece depolamak değil, **anlamlandırmak**
- Uzun metinlerle çalışırken token/latency maliyetini **kontrol etmek**
- Aynı isteği tekrar tekrar üretmek yerine **akıllı cache** kullanmak
- Hem teknik kullanıcıya hem teknik olmayan kullanıcıya iyi bir deneyim sunmak

Bu yüzden proje; veri modeli, parser, AI servisleri ve API katmanını birlikte ele alan uçtan uca bir sistem tasarımı içeriyor.

---

## 🧠 Teknik Olmayanlar İçin Kısa Açıklama

Bir kullanıcı kitap yüklediğinde sistem:

1. Kitabı küçük anlamlı parçalara böler
2. Bu parçaları veritabanına kaydeder
3. “Sor-Cevap”, “Çeviri”, “Özet” gibi AI işlemlerini bu parçalar üstünden yapar
4. Aynı özet daha önce üretildiyse yeniden AI çağrısı yapmadan cache’ten döndürür

Sonuç: Daha hızlı cevap, daha düşük maliyet, daha tutarlı çıktı.

---

## 🏗️ Mimari Özeti

- **API Katmanı**: FastAPI
- **Auth**: JWT
- **Veritabanı**: PostgreSQL + SQLAlchemy
- **Migration**: Alembic
- **Arka Plan İşleri**: Celery + Redis (opsiyonel)
- **Doküman İşleme**:
  - PDF: PyMuPDF
  - EPUB: ebooklib + BeautifulSoup
- **Vektör Arama (RAG)**: Qdrant
- **Embedding**: sentence-transformers (`all-MiniLM-L6-v2`)
- **LLM**: Google Gemini

---

## 🧩 Öne Çıkan Ürün Özellikleri

- PDF/EPUB upload ve işleme durum takibi (`pending`, `processing`, `completed`, `failed`)
- Sayfa/blok bazlı içerik erişimi
- Kitap istatistikleri
- RAG tabanlı soru-cevap (`/ask`)
- Bağlamsal çeviri (sliding window: önceki + mevcut + sonraki blok)
- Tek sayfa özetleme
- **Kitap/Bölüm Map-Reduce özetleme**
- **Özet ve çeviri cache mekanizması**

---

## ⚡ Zor Kısımlar ve Mühendislik Çözümleri

### 1) Uzun Metinlerde Token Limiti
**Problem:** Kitabın tamamını tek LLM çağrısında özetlemek pratik değil.

**Çözüm:** Map-Reduce yaklaşımı:
- Metni chunk’lara böl
- Her chunk’ı özetle (Map)
- Chunk özetlerini birleştirip final özet üret (Reduce)

### 2) Rate Limit ve Maliyet Yönetimi
**Problem:** Ücretsiz/limitli API kullanımında çok çağrı sistemi zorlar.

**Çözüm:**
- Chunk çağrıları arasında kontrollü bekleme
- Aynı isteklerde veritabanı cache kullanımı

### 3) Çıktı Tutarlılığı (Terim Birliği)
**Problem:** AI farklı çağrılarda aynı terimi farklı çevirebiliyor.

**Çözüm:**
- Kitaba özel glossary üretimi
- İlgili metin için glossary filtreleme
- Çeviri ve özette terim bağlamı kullanımı

### 4) Veri Modeli Evrimi
**Problem:** Sayfa bazlı model, RAG senaryoları için yetersiz kalıyor.

**Çözüm:**
- `BookPage` yaklaşımından `BookBlock` mimarisine geçiş
- Vektör kimliği (`vector_id`) ile retrieval optimizasyonu
- Alembic migration ile güvenli geçiş

---

## 🗃️ Cache Stratejisi

### Çeviri Cache
- Model: `TranslatedBlock`
- Anahtar mantığı: `(block_id, target_language)`

### Özet Cache
- Model: `BookSummary`
- Anahtar mantığı: `(book_id, target_language, start_page, end_page)`
- Aynı kapsam tekrar istenirse LLM’e gitmeden doğrudan DB’den dönülür

Bu yaklaşım performansı artırır ve maliyeti düşürür.

---

## 🔌 API Özeti

### Auth (`/api/v1/auth`)
- `POST /signup`
- `POST /login`
- `GET /me`

### Books (`/api/v1/books`)
- `POST /upload`
- `GET /`
- `GET /{book_id}`
- `DELETE /{book_id}`
- `GET /{book_id}/status`
- `GET /{book_id}/pages`
- `GET /{book_id}/pages/{page_number}`
- `GET /{book_id}/pages/range?start=&end=`
- `GET /{book_id}/stats`

### AI (`/api/v1/books`)
- `POST /{book_id}/ask`
- `POST /{book_id}/pages/{page_number}/translate`
- `POST /{book_id}/pages/{page_number}/summarize`
- `POST /{book_id}/summarize`  ← Map-Reduce + cache

---

## 🧪 Örnek: Kitap/Bölüm Özetleme

`POST /api/v1/books/{book_id}/summarize`

```json
{
  "target_lang": "tr",
  "start_page": 1,
  "end_page": 25
}
```

İçeride olanlar:
1. Önce `BookSummary` cache kontrolü
2. Cache yoksa Map-Reduce pipeline
3. Sonucun cache’e yazılması
4. Response dönülmesi

---

## 🛠️ Lokal Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
alembic upgrade head
```

```bash
uvicorn app.main:app --reload
```

Opsiyonel worker:

```bash
celery -A app.books.book_tasks.celery_app worker --loglevel=info
```

---

## 📁 Kod Yapısı (Kısa)

```text
app/
├── main.py
├── core/
│   └── config.py
├── users/
└── books/
    ├── models.py
    ├── router.py
    ├── page_router.py
    ├── ai_router.py
    ├── page_repository.py
    ├── parser.py
    ├── pdf_parser.py
    ├── epub_parser.py
    └── book_tasks.py
```

---

## 🎯 Bu Projede Ne Gösteriliyor?

- Ürün ihtiyacını teknik tasarıma çevirme
- Monolit içinde temiz katmanlama (router/service/repository)
- LLM/RAG uygulamalarında maliyet-performans optimizasyonu
- Migration ve model evrimi yönetimi
- API güvenliği, gözlemlenebilirlik ve bakım kolaylığına odaklı backend geliştirme

---

## 🔭 Sonraki Adımlar

- Observability (request tracing + token/cost metrics)
- Asenkron summary queue ve progress endpoint
- Hybrid search (BM25 + vector)
- Test coverage ve benchmark raporları

---

## 📌 Kısa Özet

Bu proje, klasik bir eBook backend’inden daha fazlası: **AI özelliklerinin gerçek hayattaki limitlerine (token, latency, maliyet, tutarlılık) mühendislik çözümleri üreten** bir sistem demonstrasyonu.
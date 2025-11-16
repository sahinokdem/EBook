from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.users.router import router as users_router
from app.books.router import router as books_router


"""
FastAPI Application - Main entry point.

Bu dosya:
1. FastAPI app instance oluşturur
2. Middleware'leri ekler (CORS, etc.)
3. Router'ları include eder
4. Startup/shutdown events
"""


# FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI-Powered Interactive eBook Application API",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc"     # ReDoc UI
)

"""
FastAPI app config:
- title: API ismi (Swagger UI'da görünür)
- version: API versiyonu
- description: API açıklaması
- docs_url: Swagger UI endpoint (/docs)
- redoc_url: ReDoc UI endpoint (/redoc)

Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
"""


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production'da spesifik origin'ler kullan!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
CORS (Cross-Origin Resource Sharing):
- Frontend farklı domain'den API'yi çağırabilir
- Browser security özelliği

allow_origins=["*"]:
- Development için tüm origin'lere izin ver
- Production'da: ["https://yourdomain.com", "https://app.yourdomain.com"]

allow_credentials=True:
- Cookie'lere izin ver (şimdilik kullanmıyoruz ama ileride)

allow_methods=["*"]:
- Tüm HTTP method'lara izin ver (GET, POST, PUT, DELETE, etc.)

allow_headers=["*"]:
- Tüm header'lara izin ver (Authorization, Content-Type, etc.)
"""


# Include routers
app.include_router(
    users_router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

"""
users_router include:
- prefix="/api/v1/auth": Tüm endpoint'ler bu prefix ile başlar
- tags=["Authentication"]: Swagger UI'da gruplandırma

Endpoints:
- POST /api/v1/auth/signup
- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
"""

app.include_router(
    books_router,
    prefix=f"{settings.API_V1_PREFIX}/books",
    tags=["Books"]
)

"""
books_router include:
- prefix="/api/v1/books"
- tags=["Books"]

Endpoints:
- POST /api/v1/books/upload
- GET /api/v1/books
- GET /api/v1/books/{book_id}
- DELETE /api/v1/books/{book_id}
"""


# Root endpoint
@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint - API health check.
    
    Response:
    ```json
    {
        "message": "Welcome to eBook API",
        "version": "1.0.0",
        "docs": "/docs"
    }
    ```
    """
    return {
        "message": "Welcome to eBook API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint - Monitoring için.
    
    Kullanım:
    - Docker health check
    - Load balancer health check
    - Monitoring tools (Prometheus, Grafana, etc.)
    
    Response:
    ```json
    {
        "status": "healthy"
    }
    ```
    """
    return {"status": "healthy"}


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    
    Burası uygulama başlarken bir kez çalışır.
    
    Yapılabilecekler:
    - Database connection test
    - Cache warmup
    - Background tasks start
    - Logger setup
    """
    print("🚀 Application starting...")
    print(f"📚 {settings.PROJECT_NAME}")
    print(f"🔗 Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"📖 Docs: http://localhost:8000/docs")
    
    # Upload directory oluştur
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"📁 Upload directory: {settings.UPLOAD_DIR}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    
    Uygulama kapanırken çalışır.
    
    Yapılabilecekler:
    - Database connections close
    - Background tasks stop
    - Cleanup operations
    """
    print("👋 Application shutting down...")


"""
FastAPI App Structure Summary:

1. App Instance: FastAPI()
2. Middleware: CORS
3. Routers: users_router, books_router
4. Events: startup, shutdown

Run application:
    uvicorn app.main:app --reload

- app.main: app/main.py dosyası
- app: FastAPI instance variable
- --reload: Development mode (auto-reload)

Production:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
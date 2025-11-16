from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings


# SQLAlchemy Engine - Database'e connection pool oluşturur
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Her connection'dan önce "SELECT 1" gönderir (connection health check)
    pool_size=5,          # Connection pool boyutu (5 concurrent connection)
    max_overflow=10       # Pool doluysa 10 tane daha oluşturabilir (toplam 15)
)

"""
Engine nedir?
- Database'e bağlantı havuzu (connection pool)
- Her request için yeni connection açmak yerine pool'dan alır (performans++)
- Thread-safe (güvenli)
"""

# SessionLocal - Database session factory
SessionLocal = sessionmaker(
    autocommit=False,  # Manuel commit yapmamız gerekir (güvenlik)
    autoflush=False,   # Manuel flush yapmamız gerekir (control++)
    bind=engine        # Hangi database engine'i kullanacak
)

"""
Session nedir?
- Database ile konuşmak için kullanılan object
- Transaction yönetimi (commit, rollback)
- Her request için yeni bir session oluşturulur
- Request bitince close edilir
"""

# Base - Tüm modeller bundan inherit eder
Base = declarative_base()

"""
Declarative Base nedir?
- SQLAlchemy ORM için base class
- Tüm model classları bundan türer
- Metadata tutar (table isimleri, columnlar, etc.)
"""


def get_db():
    """
    Database session dependency - FastAPI dependency injection için.
    
    Nasıl çalışır?
    1. Her request için yeni bir session oluşturur
    2. Request işlemi boyunca bu session kullanılır
    3. Request bitince session close edilir (finally block)
    
    Yield nedir?
    - Generator function (return yerine yield)
    - "db" object'i yield edilir, route handler'da kullanılır
    - Handler bittikten sonra finally block çalışır
    
    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db  # Bu satırda durur, route handler çalışır
    finally:
        db.close()  # Route handler bittikten sonra çalışır
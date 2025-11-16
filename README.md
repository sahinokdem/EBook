# eBook API

AI-Powered Interactive eBook Application - Backend API

## Features

- 🔐 JWT Authentication (Sign up, Login, Logout)
- 📚 Book Upload (PDF, EPUB)
- 📖 Book Management (List, Get, Delete)
- 🗄️ PostgreSQL Database
- 🚀 FastAPI Framework
- 📝 Automatic API Documentation (Swagger UI)

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migration:** Alembic
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt

## Local Development

### Prerequisites

- Python 3.12+
- PostgreSQL

### Setup

1. Clone the repository
```bash
git clone <your-repo-url>
cd ebook-api
```

2. Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` file
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Create database
```bash
createdb ebook
```

6. Run migrations
```bash
alembic upgrade head
```

7. Run the application
```bash
uvicorn app.main:app --reload
```

8. Open API documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Create new account
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

### Books
- `POST /api/v1/books/upload` - Upload book
- `GET /api/v1/books` - List books (paginated)
- `GET /api/v1/books/{book_id}` - Get book details
- `DELETE /api/v1/books/{book_id}` - Delete book

## Deployment

### Render

1. Push to GitHub
2. Connect repository to Render
3. Render will auto-detect `render.yaml`
4. Database and web service will be created automatically

### Manual Render Setup

1. Create PostgreSQL database on Render
2. Create Web Service
3. Set environment variables:
   - `DATABASE_URL` (from database)
   - `JWT_SECRET_KEY`
   - `JWT_ALGORITHM=HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES=30`

## Project Structure

```
ebook-api/
├── app/
│   ├── main.py              # FastAPI app
│   ├── core/                # Core utilities
│   │   ├── config.py
│   │   └── security.py
│   ├── shared/              # Shared resources
│   │   ├── database.py
│   │   └── dependencies.py
│   ├── users/               # Users domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   └── books/               # Books domain
│       ├── models.py
│       ├── schemas.py
│       ├── repository.py
│       ├── service.py
│       └── router.py
├── alembic/                 # Database migrations
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT

## Authors

- Şahin Ökdem
- Ege Ünlü

## Supervisor

Dr. Buket Erşahin
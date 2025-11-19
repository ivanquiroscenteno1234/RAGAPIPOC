# NotebookLM-Style RAG Application Backend

A FastAPI-based backend for a NotebookLM-style RAG (Retrieval-Augmented Generation) application using AWS Bedrock Knowledge Bases and Google Gemini.

## Architecture

- **FastAPI**: REST API framework
- **PostgreSQL**: Relational database for structured data
- **AWS S3**: Document storage
- **AWS Bedrock Knowledge Bases**: Vector storage and retrieval
- **Google Gemini**: LLM for answering questions
- **LangChain**: RAG orchestration

## Features

- User authentication with JWT
- Notebook management (CRUD operations)
- Document upload and ingestion to Bedrock KB
- Chat interface with citation support
- Metadata-filtered retrieval for multi-tenancy

## Project Structure

```
RAGAppPCOApi/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/              # API v1 endpoints
│   │       ├── __init__.py
│   │       ├── auth.py      # Authentication endpoints
│   │       ├── notebooks.py # Notebook endpoints
│   │       ├── documents.py # Document endpoints
│   │       └── chats.py     # Chat endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py  # Authentication logic
│   │   ├── rag_service.py   # RAG orchestration
│   │   └── ingestion.py     # Document ingestion
│   └── schemas/
│       ├── __init__.py
│       └── ...              # Pydantic schemas
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- AWS Account with access to S3 and Bedrock
- Google Cloud account with Gemini API access

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd RAGAppPCOApi
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
# Create the database
createdb ragapp

# Run migrations
alembic upgrade head
```

### Running the Application

Development mode:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register a new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Notebooks
- `GET /api/v1/notebooks` - List user's notebooks
- `POST /api/v1/notebooks` - Create a new notebook
- `GET /api/v1/notebooks/{id}` - Get notebook details
- `PATCH /api/v1/notebooks/{id}` - Update notebook
- `DELETE /api/v1/notebooks/{id}` - Delete notebook

### Documents
- `GET /api/v1/notebooks/{id}/documents` - List notebook documents
- `POST /api/v1/notebooks/{id}/documents` - Upload document
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/{id}/ingest` - Re-trigger ingestion

### Chats
- `POST /api/v1/notebooks/{id}/chats` - Create a new chat
- `GET /api/v1/notebooks/{id}/chats` - List notebook chats
- `GET /api/v1/chats/{id}` - Get chat details
- `POST /api/v1/chats/{id}/messages` - Send a message
- `GET /api/v1/chats/{id}/messages` - Get chat messages

## Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ragapp

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
BEDROCK_KB_ID=your-kb-id

# Gemini
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-pro

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

## Development Phases

- ✅ **Phase 0**: Project setup and structure
- 🔄 **Phase 1**: Auth + Core Models
- ⏳ **Phase 2**: Bedrock KB Ingestion
- ⏳ **Phase 3**: RAG Service and Chat
- ⏳ **Phase 4**: Polish and Observability
- ⏳ **Phase 5**: Advanced Features

## License

[Your License Here]

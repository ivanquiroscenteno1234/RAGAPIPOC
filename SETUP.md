# Setup Guide for NotebookLM-Style RAG API

This guide will help you set up and run the application.

## Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher
- AWS Account (with S3 and Bedrock access)
- Google Cloud account (for Gemini API)

## Step 1: Install Dependencies

### Create and activate virtual environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate

# On Linux/Mac:
# source venv/bin/activate
```

### Install Python packages

```powershell
pip install -r requirements.txt
```

## Step 2: Set Up PostgreSQL Database

```powershell
# Using psql or pgAdmin, create a database
createdb ragapp

# Or using SQL:
# CREATE DATABASE ragapp;
```

## Step 3: Configure Environment Variables

```powershell
# Copy the example environment file
copy .env.example .env

# Edit .env with your actual values
notepad .env
```

Required configuration:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Generate a secure random key (e.g., `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `S3_BUCKET_NAME`: Your S3 bucket name
- `BEDROCK_KB_ID`: Your Bedrock Knowledge Base ID
- `GEMINI_API_KEY`: Your Google Gemini API key

## Step 4: Initialize Database

```powershell
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## Step 5: Run the Application

```powershell
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Next Steps

### Phase 2 - Bedrock KB Ingestion

The current implementation has document upload to S3 working, but you'll need to:

1. Set up an AWS Bedrock Knowledge Base
2. Implement the ingestion worker in `app/services/ingestion.py`
3. Configure background task processing

### Phase 3 - RAG Service

Implement the RAG service to:

1. Build metadata-filtered retrievers
2. Integrate with Gemini for answer generation
3. Store citations

## Testing the API

### Register a user

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Create a notebook

```bash
curl -X POST "http://localhost:8000/api/v1/notebooks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "name": "My First Notebook",
    "description": "A test notebook"
  }'
```

## Troubleshooting

### Database connection errors

- Verify PostgreSQL is running
- Check your `DATABASE_URL` in `.env`
- Ensure the database user has appropriate permissions

### AWS/Bedrock errors

- Verify AWS credentials are correct
- Check IAM permissions for S3 and Bedrock access
- Ensure S3 bucket exists and is accessible

### Import errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're in the virtual environment

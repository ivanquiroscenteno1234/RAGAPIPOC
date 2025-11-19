# API Documentation - NotebookLM-Style RAG Backend

Base URL: `http://localhost:8000`

---

## Table of Contents
1. [Health & Info](#health--info)
2. [Authentication](#authentication)
3. [Notebooks](#notebooks)
4. [Documents](#documents)
5. [Chats](#chats)
6. [Messages](#messages)
7. [Legacy/Compatibility](#legacy-compatibility)

---

## Health & Info

### Get Root Info
```
GET http://localhost:8000/
```

**Request Body:** None

**Response:**
```json
{
  "message": "NotebookLM-Style RAG API",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

---

### Health Check
```
GET http://localhost:8000/api/v1/health
```

**Request Body:** None

**Response:**
```json
{
  "status": "healthy",
  "service": "NotebookLM RAG API",
  "version": "1.0.0"
}
```

---

## Authentication

> **Note:** Auth endpoints do NOT require authentication. All other endpoints require a JWT token in the `Authorization` header.

### Signup
```
POST http://localhost:8000/api/v1/auth/signup
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `201 Created`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

### Login
```
POST http://localhost:8000/api/v1/auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Usage:** Include token in subsequent requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### Get Current User
```
GET http://localhost:8000/api/v1/auth/me
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

## Notebooks

> **Authentication Required:** All notebook endpoints require JWT token

### List Notebooks
```
GET http://localhost:8000/api/v1/notebooks
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Research Notes",
    "description": "My main research notebook",
    "created_at": "2025-11-18T16:00:00.000Z",
    "updated_at": "2025-11-18T16:00:00.000Z"
  }
]
```

---

### Create Notebook
```
POST http://localhost:8000/api/v1/notebooks
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "Research Notes",
  "description": "My main research notebook"
}
```

**Response:** `201 Created`
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Research Notes",
  "description": "My main research notebook",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

### Get Notebook
```
GET http://localhost:8000/api/v1/notebooks/{notebook_id}
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Research Notes",
  "description": "My main research notebook",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

### Update Notebook
```
PATCH http://localhost:8000/api/v1/notebooks/{notebook_id}
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "name": "Updated Research Notes",
  "description": "Updated description"
}
```

> **Note:** Both fields are optional. Only provided fields will be updated.

**Response:** `200 OK`
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Updated Research Notes",
  "description": "Updated description",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:05:00.000Z"
}
```

---

### Delete Notebook
```
DELETE http://localhost:8000/api/v1/notebooks/{notebook_id}
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `204 No Content`

---

## Documents

> **Authentication Required:** All document endpoints require JWT token

### List Documents in Notebook
```
GET http://localhost:8000/api/v1/notebooks/{notebook_id}/documents
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
[
  {
    "id": "789e0123-e89b-12d3-a456-426614174000",
    "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "research_paper.pdf",
    "original_filename": "research_paper.pdf",
    "s3_key": "users/123e4567.../notebooks/456e7890.../abc123.pdf",
    "status": "ready",
    "error_message": null,
    "created_at": "2025-11-18T16:00:00.000Z",
    "updated_at": "2025-11-18T16:02:00.000Z"
  }
]
```

**Document Status Values:**
- `pending` - Uploaded, waiting for ingestion
- `ingesting` - Currently being processed by Bedrock KB
- `ready` - Available for RAG retrieval
- `error` - Ingestion failed (see error_message)

---

### Upload Document
```
POST http://localhost:8000/api/v1/notebooks/{notebook_id}/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Request Body:** (multipart/form-data)
```
file: <binary file data>
```

**Example with cURL:**
```bash
curl -X POST http://localhost:8000/api/v1/notebooks/{notebook_id}/documents \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/document.pdf"
```

**Response:** `201 Created`
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174000",
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "research_paper.pdf",
  "original_filename": "research_paper.pdf",
  "s3_key": "users/123e4567.../notebooks/456e7890.../abc123.pdf",
  "status": "pending",
  "error_message": null,
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

> **Note:** Ingestion is triggered automatically. Status will transition from `pending` → `ingesting` → `ready`.

---

### Get Document
```
GET http://localhost:8000/api/v1/documents/{document_id}
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174000",
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "research_paper.pdf",
  "original_filename": "research_paper.pdf",
  "s3_key": "users/123e4567.../notebooks/456e7890.../abc123.pdf",
  "status": "ready",
  "error_message": null,
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:02:00.000Z"
}
```

---

### Delete Document
```
DELETE http://localhost:8000/api/v1/documents/{document_id}
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `204 No Content`

> **Note:** Deletes from both S3 and database.

---

### Re-Trigger Ingestion
```
POST http://localhost:8000/api/v1/documents/{document_id}/ingest
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174000",
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "research_paper.pdf",
  "original_filename": "research_paper.pdf",
  "s3_key": "users/123e4567.../notebooks/456e7890.../abc123.pdf",
  "status": "ingesting",
  "error_message": null,
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:10:00.000Z"
}
```

> **Note:** Use this to retry failed ingestions or re-ingest after errors.

---

## Chats

> **Authentication Required:** All chat endpoints require JWT token

### Create Chat
```
POST http://localhost:8000/api/v1/notebooks/{notebook_id}/chats
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "Questions about Research Paper"
}
```

**Response:** `201 Created`
```json
{
  "id": "abc12345-e89b-12d3-a456-426614174000",
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Questions about Research Paper",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

### List Chats in Notebook
```
GET http://localhost:8000/api/v1/notebooks/{notebook_id}/chats
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
[
  {
    "id": "abc12345-e89b-12d3-a456-426614174000",
    "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Questions about Research Paper",
    "created_at": "2025-11-18T16:00:00.000Z",
    "updated_at": "2025-11-18T16:00:00.000Z"
  }
]
```

---

### Get Chat
```
GET http://localhost:8000/api/v1/chats/{chat_id}
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
{
  "id": "abc12345-e89b-12d3-a456-426614174000",
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Questions about Research Paper",
  "created_at": "2025-11-18T16:00:00.000Z",
  "updated_at": "2025-11-18T16:00:00.000Z"
}
```

---

## Messages

> **Authentication Required:** All message endpoints require JWT token

### List Messages in Chat
```
GET http://localhost:8000/api/v1/chats/{chat_id}/messages
Authorization: Bearer <token>
```

**Request Body:** None

**Response:** `200 OK`
```json
[
  {
    "id": "def45678-e89b-12d3-a456-426614174000",
    "chat_id": "abc12345-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "role": "user",
    "content": "What are the main findings?",
    "metadata": null,
    "created_at": "2025-11-18T16:00:00.000Z",
    "updated_at": "2025-11-18T16:00:00.000Z"
  },
  {
    "id": "ghi78901-e89b-12d3-a456-426614174000",
    "chat_id": "abc12345-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "role": "assistant",
    "content": "Based on the documents, the main findings are... [Doc: research_paper.pdf, Chunk: chunk_1]",
    "metadata": {
      "model": "gemini",
      "chunks_retrieved": 3
    },
    "created_at": "2025-11-18T16:00:05.000Z",
    "updated_at": "2025-11-18T16:00:05.000Z"
  }
]
```

**Message Roles:**
- `user` - Message from the user
- `assistant` - AI-generated response
- `system` - System messages (rarely used)

---

### Send Message (Triggers RAG)
```
POST http://localhost:8000/api/v1/chats/{chat_id}/messages
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "content": "What are the main findings?",
  "selected_document_ids": [
    "789e0123-e89b-12d3-a456-426614174000"
  ]
}
```

> **Note:** `selected_document_ids` is optional. If provided, only those documents will be searched. If omitted, all documents in the notebook are searched.

**Response:** `201 Created`
```json
{
  "id": "ghi78901-e89b-12d3-a456-426614174000",
  "chat_id": "abc12345-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role": "assistant",
  "content": "Based on the documents, the main findings are:\n\n1. The study found significant correlations... [Doc: research_paper.pdf, Chunk: chunk_1]\n2. Additionally, the data shows... [Doc: research_paper.pdf, Chunk: chunk_3]",
  "metadata": {
    "model": "gemini",
    "chunks_retrieved": 3
  },
  "created_at": "2025-11-18T16:00:05.000Z",
  "updated_at": "2025-11-18T16:00:05.000Z"
}
```

> **Note:** This endpoint:
> 1. Stores the user's message
> 2. Retrieves relevant chunks from Bedrock KB (filtered by user/notebook/documents)
> 3. Calls Gemini with context and strict prompt
> 4. Stores the assistant's response with citations
> 5. Returns the assistant's message

---

## Legacy Compatibility

> **Note:** These endpoints support existing frontends without the `/api/v1` prefix.

### List Documents (Legacy)
```
GET http://localhost:8000/api/documents?notebook_id={notebook_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `notebook_id` (optional) - Filter by notebook

**Request Body:** None

**Response:** `200 OK`
```json
[
  {
    "id": "789e0123-e89b-12d3-a456-426614174000",
    "title": "research_paper.pdf",
    "filename": "research_paper.pdf",
    "status": "ready",
    "notebook_id": "456e7890-e89b-12d3-a456-426614174000",
    "uploaded_at": "2025-11-18T16:00:00.000Z"
  }
]
```

---

### Chat (Legacy)
```
POST http://localhost:8000/api/chat
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "message": "What are the main findings?",
  "history": [
    {
      "role": "user",
      "content": "Previous question"
    },
    {
      "role": "assistant",
      "content": "Previous answer"
    }
  ],
  "selectedDocumentIds": [
    "789e0123-e89b-12d3-a456-426614174000"
  ],
  "notebook_id": "456e7890-e89b-12d3-a456-426614174000"
}
```

**Response:** `200 OK`
```json
{
  "answer": "Based on the documents, the main findings are... [Doc: research_paper.pdf, Chunk: chunk_1]",
  "sources": [
    {
      "document_id": "789e0123-e89b-12d3-a456-426614174000",
      "filename": "research_paper.pdf",
      "chunk_id": "chunk_1",
      "snippet": "The study found significant correlations between...",
      "score": 0.85
    }
  ]
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

### 400 Bad Request
```json
{
  "detail": "Invalid request format"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Notebook not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to upload file to S3"
}
```

---

## Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide a web interface to test all endpoints directly in your browser!

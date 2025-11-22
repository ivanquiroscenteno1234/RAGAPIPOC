"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title="NotebookLM-Style RAG API",
    description="Backend for NotebookLM-style RAG application with AWS Bedrock and Gemini",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "NotebookLM RAG API",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "NotebookLM-Style RAG API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# Import routers
from app.api.v1 import auth, notebooks, documents, chats, summary_packs
from app.api import compatibility

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(notebooks.router, prefix="/api/v1", tags=["notebooks"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(chats.router, prefix="/api/v1", tags=["chats"])
app.include_router(summary_packs.router, prefix="/api/v1", tags=["summary_packs"])

# Include compatibility endpoints (no prefix for legacy paths)
app.include_router(compatibility.router, tags=["compatibility"])

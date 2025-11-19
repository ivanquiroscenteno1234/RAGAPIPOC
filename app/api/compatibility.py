"""Compatibility endpoints for existing frontend."""
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Document, DocumentStatus
from app.services.auth_service import get_current_user

router = APIRouter()


# Legacy schemas for compatibility
class LegacyDocumentResponse(BaseModel):
    """Legacy document response format."""
    id: str
    title: str
    filename: str
    status: str
    notebook_id: str
    uploaded_at: str


class LegacyChatRequest(BaseModel):
    """Legacy chat request format."""
    message: str
    history: List[Dict[str, str]] = []
    selectedDocumentIds: List[str] = []
    notebook_id: str


class LegacyChatResponse(BaseModel):
    """Legacy chat response format."""
    answer: str
    sources: List[Dict[str, Any]] = []


@router.get("/api/documents", response_model=List[LegacyDocumentResponse])
def list_documents_legacy(
    notebook_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List documents (legacy endpoint for existing frontend)."""
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if notebook_id:
        try:
            query = query.filter(Document.notebook_id == UUID(notebook_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid notebook_id format"
            )
    
    documents = query.all()
    
    # Transform to legacy format
    legacy_docs = []
    for doc in documents:
        legacy_docs.append(LegacyDocumentResponse(
            id=str(doc.id),
            title=doc.title,
            filename=doc.original_filename,
            status=doc.status.value,
            notebook_id=str(doc.notebook_id),
            uploaded_at=doc.created_at.isoformat()
        ))
    
    return legacy_docs


@router.post("/api/chat", response_model=LegacyChatResponse)
def chat_legacy(
    request: LegacyChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat endpoint (legacy endpoint for existing frontend)."""
    from app.services.rag_service import answer_question
    from app.models import Message, MessageRole
    
    try:
        notebook_id = UUID(request.notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notebook_id format"
        )
    
    # Convert selected document IDs
    selected_doc_ids = None
    if request.selectedDocumentIds:
        try:
            selected_doc_ids = [UUID(doc_id) for doc_id in request.selectedDocumentIds]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format"
            )
    
    # Convert history to Message objects (simplified)
    history_messages = []
    for hist_msg in request.history:
        role = MessageRole.USER if hist_msg.get('role') == 'user' else MessageRole.ASSISTANT
        msg = Message(
            role=role,
            content=hist_msg.get('content', ''),
            user_id=current_user.id,
            chat_id=None  # Not persisted
        )
        history_messages.append(msg)
    
    # Call RAG service
    answer, chunks = answer_question(
        user_id=current_user.id,
        notebook_id=notebook_id,
        question=request.message,
        history=history_messages,
        selected_document_ids=selected_doc_ids
    )
    
    # Format sources
    sources = []
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        sources.append({
            'document_id': metadata.get('document_id', 'unknown'),
            'filename': metadata.get('filename', 'unknown'),
            'chunk_id': chunk.get('chunk_id', 'unknown'),
            'snippet': chunk.get('content', '')[:200],
            'score': chunk.get('score', 0.0)
        })
    
    return LegacyChatResponse(
        answer=answer,
        sources=sources
    )

"""Chat and message endpoints."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notebook, Chat, Message, MessageRole, Citation, Document
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.services.auth_service import get_current_user
from app.services.rag_service import answer_question

router = APIRouter()


@router.post("/notebooks/{notebook_id}/chats", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    notebook_id: UUID,
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat in a notebook."""
    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.user_id == current_user.id
    ).first()
    
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    
    new_chat = Chat(
        notebook_id=notebook_id,
        user_id=current_user.id,
        title=chat_data.title
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    
    return new_chat


@router.get("/notebooks/{notebook_id}/chats", response_model=List[ChatResponse])
def list_chats(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chats in a notebook."""
    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.user_id == current_user.id
    ).first()
    
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    
    chats = db.query(Chat).filter(Chat.notebook_id == notebook_id).all()
    return chats


@router.get("/chats/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific chat."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return chat


@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponse])
def list_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all messages in a chat."""
    # Verify chat ownership
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    return messages


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message in a chat and get AI response."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        # Verify chat ownership and get notebook
        chat = db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        ).first()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Create user message
        user_message = Message(
            chat_id=chat_id,
            user_id=current_user.id,
            role=MessageRole.USER,
            content=message_data.content,
            metadata_={"selected_document_ids": [str(doc_id) for doc_id in message_data.selected_document_ids]} if message_data.selected_document_ids else None
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # Get chat history (exclude current message)
        history = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.id != user_message.id
        ).order_by(Message.created_at).all()
        
        # Call RAG service
        answer, retrieved_chunks = answer_question(
            user_id=current_user.id,
            notebook_id=chat.notebook_id,
            question=message_data.content,
            history=history,
            selected_document_ids=message_data.selected_document_ids,
            mode=message_data.mode
        )
        
        # Ensure answer is a string
        if isinstance(answer, (list, dict)):
            import json
            answer = json.dumps(answer)
            
        # Create assistant message
        assistant_message = Message(
            chat_id=chat_id,
            user_id=current_user.id,
            role=MessageRole.ASSISTANT,
            content=str(answer),
            metadata_={"model": "gemini", "chunks_retrieved": len(retrieved_chunks)}
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # Store citations
        for chunk in retrieved_chunks:
            metadata = chunk.get('metadata', {})
            doc_id_str = metadata.get('document_id')
            
            if doc_id_str:
                try:
                    # Find document in database
                    document = db.query(Document).filter(
                        Document.id == UUID(doc_id_str)
                    ).first()
                    
                    if document:
                        citation = Citation(
                            message_id=assistant_message.id,
                            document_id=document.id,
                            source_chunk_id=chunk.get('chunk_id', 'unknown'),
                            snippet=chunk.get('content', '')[:500],  # Limit snippet length
                            location=chunk.get('location', {})
                        )
                        db.add(citation)
                except Exception as e:
                    # Log error but don't fail the request
                    import logging
                    logging.error(f"Error creating citation: {e}")
        
        db.commit()
        
        return assistant_message
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


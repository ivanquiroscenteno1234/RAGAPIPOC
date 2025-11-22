"""Pydantic schemas for chats and messages."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ValidationInfo, model_validator
from typing import Optional, List, Dict, Any
from app.models import MessageRole


class ChatBase(BaseModel):
    """Base chat schema."""
    title: str = Field(..., min_length=1, max_length=255)


class ChatCreate(ChatBase):
    """Schema for creating a chat."""
    pass


class ChatResponse(ChatBase):
    """Schema for chat response."""
    id: UUID
    notebook_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base message schema."""
    role: MessageRole
    content: str
    metadata_content: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata", validation_alias="metadata_")


class MessageCreate(BaseModel):
    """Schema for creating a message (user question)."""
    content: str
    selected_document_ids: Optional[List[UUID]] = None
    mode: Optional[str] = "ask"  # "ask" or "plan"



class MessageResponse(MessageBase):
    """Schema for message response."""
    id: UUID
    chat_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CitationResponse(BaseModel):
    """Schema for citation response."""
    id: UUID
    message_id: UUID
    document_id: UUID
    source_chunk_id: str
    snippet: str
    location: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageWithCitations(MessageResponse):
    """Schema for message with citations."""
    citations: List[CitationResponse] = []

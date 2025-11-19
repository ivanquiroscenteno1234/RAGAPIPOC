"""Pydantic schemas for documents."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional
from app.models import DocumentStatus


class DocumentBase(BaseModel):
    """Base document schema."""
    title: str = Field(..., min_length=1, max_length=255)


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    pass


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: UUID
    notebook_id: UUID
    user_id: UUID
    original_filename: str
    s3_key: str
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

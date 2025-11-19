"""Pydantic schemas for notebooks."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional


class NotebookBase(BaseModel):
    """Base notebook schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class NotebookCreate(NotebookBase):
    """Schema for creating a notebook."""
    pass


class NotebookUpdate(BaseModel):
    """Schema for updating a notebook."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class NotebookResponse(NotebookBase):
    """Schema for notebook response."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

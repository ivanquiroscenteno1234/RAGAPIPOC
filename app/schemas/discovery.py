from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models import (
    DiscoveryQuestionSetStatus,
    DiscoveryQuestionTargetAudience,
    DiscoveryQuestionScope,
    DiscoveryQuestionCategory,
    DiscoveryQuestionPriority,
    DiscoveryQuestionStatus,
)


class DiscoveryQuestionBase(BaseModel):
    text: str
    category: DiscoveryQuestionCategory
    priority: DiscoveryQuestionPriority
    status: DiscoveryQuestionStatus = DiscoveryQuestionStatus.OPEN
    related_document_id: Optional[UUID] = None


class DiscoveryQuestionUpdate(BaseModel):
    status: DiscoveryQuestionStatus


class DiscoveryQuestion(DiscoveryQuestionBase):
    id: UUID
    question_set_id: UUID
    related_document_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscoveryQuestionSetBase(BaseModel):
    title: str
    target_audience: DiscoveryQuestionTargetAudience
    scope_type: DiscoveryQuestionScope
    scope_document_ids: Optional[List[UUID]] = None


class DiscoveryQuestionSetCreate(DiscoveryQuestionSetBase):
    pass


class DiscoveryQuestionSet(DiscoveryQuestionSetBase):
    id: UUID
    notebook_id: UUID
    created_by_user_id: UUID
    status: DiscoveryQuestionSetStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    questions: List[DiscoveryQuestion] = []

    class Config:
        from_attributes = True

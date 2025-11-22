from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models import SummaryPackStatus, SummaryPackScope

class SummaryPackBase(BaseModel):
    title: str
    scope_type: SummaryPackScope
    scope_document_ids: Optional[List[UUID]] = None

class SummaryPackCreate(SummaryPackBase):
    pass

class SummaryPackUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[SummaryPackStatus] = None
    sections: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class SummaryPackResponse(SummaryPackBase):
    id: UUID
    notebook_id: UUID
    created_by_user_id: UUID
    status: SummaryPackStatus
    sections: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

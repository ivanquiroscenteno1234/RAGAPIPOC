from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.api.v1.auth import get_current_user
from app.models import User, SummaryPack, Notebook
from app.schemas.summary_pack import SummaryPackCreate, SummaryPackResponse
from app.services.summary_service import generate_summary_pack_task

router = APIRouter()

@router.post("/notebooks/{notebook_id}/summary-packs", response_model=SummaryPackResponse, status_code=status.HTTP_201_CREATED)
def create_summary_pack(
    notebook_id: UUID,
    pack_data: SummaryPackCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new summary pack and start generation in background."""
    # Verify notebook exists and belongs to user
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id, Notebook.user_id == current_user.id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    new_pack = SummaryPack(
        notebook_id=notebook_id,
        created_by_user_id=current_user.id,
        title=pack_data.title,
        scope_type=pack_data.scope_type,
        scope_document_ids=pack_data.scope_document_ids
    )
    db.add(new_pack)
    db.commit()
    db.refresh(new_pack)

    # Trigger background task
    print(f"DEBUG: Triggering background task for pack {new_pack.id}")
    background_tasks.add_task(generate_summary_pack_task, new_pack.id)
    print("DEBUG: Background task added")

    return new_pack

@router.get("/notebooks/{notebook_id}/summary-packs", response_model=List[SummaryPackResponse])
def list_summary_packs(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all summary packs for a notebook."""
    # Verify notebook exists and belongs to user
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id, Notebook.user_id == current_user.id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    packs = db.query(SummaryPack).filter(SummaryPack.notebook_id == notebook_id).order_by(SummaryPack.created_at.desc()).all()
    return packs

@router.get("/summary-packs/{pack_id}", response_model=SummaryPackResponse)
def get_summary_pack(
    pack_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific summary pack."""
    pack = db.query(SummaryPack).filter(SummaryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Summary pack not found")
    
    if pack.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this summary pack")

    return pack


@router.delete("/summary-packs/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_summary_pack(
    pack_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a summary pack."""
    pack = db.query(SummaryPack).filter(SummaryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Summary pack not found")
    
    if pack.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this summary pack")

    db.delete(pack)
    db.commit()

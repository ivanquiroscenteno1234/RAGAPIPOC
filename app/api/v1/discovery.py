from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.api.v1.auth import get_current_user
from app.models import User, DiscoveryQuestionSet, DiscoveryQuestion, Notebook, Document
from app.schemas.discovery import DiscoveryQuestionSetCreate, DiscoveryQuestionSet as DiscoveryQuestionSetSchema, DiscoveryQuestionUpdate, DiscoveryQuestion as DiscoveryQuestionSchema
from app.services.discovery_service import generate_discovery_questions_task

router = APIRouter()

@router.post("/notebooks/{notebook_id}/discovery-question-sets", response_model=DiscoveryQuestionSetSchema, status_code=status.HTTP_201_CREATED)
def create_discovery_question_set(
    notebook_id: UUID,
    set_data: DiscoveryQuestionSetCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new discovery question set and start generation in background."""
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id, Notebook.user_id == current_user.id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    new_set = DiscoveryQuestionSet(
        notebook_id=notebook_id,
        created_by_user_id=current_user.id,
        title=set_data.title,
        target_audience=set_data.target_audience,
        scope_type=set_data.scope_type,
        scope_document_ids=set_data.scope_document_ids
    )
    db.add(new_set)
    db.commit()
    db.refresh(new_set)

    # Trigger background task
    background_tasks.add_task(generate_discovery_questions_task, new_set.id)

    return new_set

@router.get("/notebooks/{notebook_id}/discovery-question-sets", response_model=List[DiscoveryQuestionSetSchema])
def list_discovery_question_sets(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all discovery question sets for a notebook."""
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id, Notebook.user_id == current_user.id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    sets = db.query(DiscoveryQuestionSet).filter(DiscoveryQuestionSet.notebook_id == notebook_id).order_by(DiscoveryQuestionSet.created_at.desc()).all()
    
    # Populate document titles for all questions in all sets
    for s in sets:
        for q in s.questions:
            if q.related_document_id:
                doc = db.query(Document).filter(Document.id == q.related_document_id).first()
                if doc:
                    q.related_document_title = doc.title
    
    return sets

@router.get("/discovery-question-sets/{set_id}", response_model=DiscoveryQuestionSetSchema)
def get_discovery_question_set(
    set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific discovery question set."""
    q_set = db.query(DiscoveryQuestionSet).filter(DiscoveryQuestionSet.id == set_id).first()
    if not q_set:
        raise HTTPException(status_code=404, detail="Discovery question set not found")
    
    if q_set.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this discovery question set")

    # Populate document titles for all questions
    for q in q_set.questions:
        if q.related_document_id:
            doc = db.query(Document).filter(Document.id == q.related_document_id).first()
            if doc:
                q.related_document_title = doc.title

    return q_set

@router.patch("/discovery-questions/{question_id}", response_model=DiscoveryQuestionSchema)
def update_discovery_question(
    question_id: UUID,
    update_data: DiscoveryQuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a discovery question status."""
    question = db.query(DiscoveryQuestion).join(DiscoveryQuestionSet).filter(DiscoveryQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Discovery question not found")
    
    if question.question_set.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this discovery question")

    question.status = update_data.status
    db.commit()
    db.refresh(question)
    
    # Populate document title if available
    if question.related_document_id:
        doc = db.query(Document).filter(Document.id == question.related_document_id).first()
        if doc:
            question.related_document_title = doc.title
    
    return question

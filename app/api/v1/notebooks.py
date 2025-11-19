"""Notebook endpoints."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notebook
from app.schemas.notebook import NotebookCreate, NotebookUpdate, NotebookResponse
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/notebooks", response_model=List[NotebookResponse])
def list_notebooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all notebooks for the current user."""
    notebooks = db.query(Notebook).filter(Notebook.user_id == current_user.id).all()
    return notebooks


@router.post("/notebooks", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(
    notebook_data: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new notebook."""
    new_notebook = Notebook(
        user_id=current_user.id,
        name=notebook_data.name,
        description=notebook_data.description
    )
    db.add(new_notebook)
    db.commit()
    db.refresh(new_notebook)
    
    return new_notebook


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific notebook."""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.user_id == current_user.id
    ).first()
    
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    
    return notebook


@router.patch("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: UUID,
    notebook_data: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a notebook."""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.user_id == current_user.id
    ).first()
    
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    
    # Update fields
    if notebook_data.name is not None:
        notebook.name = notebook_data.name
    if notebook_data.description is not None:
        notebook.description = notebook_data.description
    
    db.commit()
    db.refresh(notebook)
    
    return notebook


@router.delete("/notebooks/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notebook."""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.user_id == current_user.id
    ).first()
    
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    
    db.delete(notebook)
    db.commit()
    
    return None

"""Document endpoints."""
from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Notebook, Document, DocumentStatus
from app.schemas.document import DocumentResponse
from app.services.auth_service import get_current_user
from app.services.s3_client import upload_file_to_s3, delete_file_from_s3
from app.services.ingestion import trigger_ingestion
from app.config import settings
from app.services.bedrock_client import start_ingestion_job

router = APIRouter()


@router.get("/notebooks/{notebook_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents in a notebook."""
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
    
    documents = db.query(Document).filter(Document.notebook_id == notebook_id).all()
    return documents


@router.post("/notebooks/{notebook_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    notebook_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document to a notebook."""
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
    
    # Generate unique S3 key
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    s3_key = f"users/{current_user.id}/notebooks/{notebook_id}/{uuid4()}.{file_extension}"
    
    # Read file content
    file_content = await file.read()
    
    # Upload to S3
    upload_success = upload_file_to_s3(
        file_content=file_content,
        s3_key=s3_key,
        content_type=file.content_type
    )
    
    if not upload_success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to S3"
        )
    
    # Create document record
    new_document = Document(
        notebook_id=notebook_id,
        user_id=current_user.id,
        title=file.filename,
        original_filename=file.filename,
        s3_key=s3_key,
        status=DocumentStatus.PENDING
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    
    # Upload metadata file to S3 for Bedrock KB filtering
    import json
    metadata = {
        "metadataAttributes": {
            "user_id": str(current_user.id),
            "notebook_id": str(notebook_id),
            "document_id": str(new_document.id),
            "filename": file.filename
        }
    }
    
    metadata_key = f"{s3_key}.metadata.json"
    upload_file_to_s3(
        file_content=json.dumps(metadata).encode('utf-8'),
        s3_key=metadata_key,
        content_type='application/json'
    )
    
    # Trigger ingestion job in background
    import asyncio
    asyncio.create_task(trigger_ingestion(new_document, db))
    
    return new_document


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete from S3
    delete_file_from_s3(document.s3_key)
    delete_file_from_s3(f"{document.s3_key}.metadata.json")
    
    # Trigger ingestion job to sync KB (remove deleted document)
    if settings.BEDROCK_KB_ID and settings.BEDROCK_DATA_SOURCE_ID:
        
        s3_uri = f"s3://{settings.S3_BUCKET_NAME}/{document.s3_key}"
        start_ingestion_job(
            knowledge_base_id=settings.BEDROCK_KB_ID,
            data_source_id=settings.BEDROCK_DATA_SOURCE_ID,
            document_id=document.id,
            user_id=document.user_id,
            notebook_id=document.notebook_id,
            s3_uri=s3_uri
        )
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    return None

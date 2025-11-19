"""Document ingestion service with background processing."""
import asyncio
import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Document, DocumentStatus
from app.config import settings
from app.services.bedrock_client import start_ingestion_job, get_ingestion_job_status

logger = logging.getLogger(__name__)

# In-memory storage for ingestion job tracking
# In production, use Redis or a proper job queue (Celery, RQ, etc.)
ingestion_jobs: dict[UUID, str] = {}


async def trigger_ingestion(
    document: Document,
    db: Session
) -> bool:
    """Trigger ingestion for a document.
    
    Args:
        document: Document model instance
        db: Database session
        
    Returns:
        True if ingestion was triggered successfully
    """
    try:
        # Check if AWS credentials are configured
        if not settings.AWS_ACCESS_KEY_ID or not settings.BEDROCK_KB_ID:
            logger.warning(f"AWS credentials not configured. Skipping Bedrock ingestion for document {document.id}")
            # Mark document as ready immediately (no ingestion)
            document.status = DocumentStatus.READY
            document.error_message = None
            db.commit()
            logger.info(f"Document {document.id} marked as READY (AWS not configured)")
            return True
        
        # Update status to ingesting
        document.status = DocumentStatus.INGESTING
        document.error_message = None
        db.commit()
        
        # Construct S3 URI
        s3_uri = f"s3://{settings.S3_BUCKET_NAME}/{document.s3_key}"
        
        # Start ingestion job
        # Note: You need to configure a data source in your Bedrock KB first
        # For now, we'll use a placeholder data source ID
        # In production, store this in settings or database
        data_source_id = settings.BEDROCK_DATA_SOURCE_ID if hasattr(settings, 'BEDROCK_DATA_SOURCE_ID') else "default-data-source"
        
        ingestion_job_id = start_ingestion_job(
            knowledge_base_id=settings.BEDROCK_KB_ID,
            data_source_id=data_source_id,
            document_id=document.id,
            user_id=document.user_id,
            notebook_id=document.notebook_id,
            s3_uri=s3_uri
        )
        
        if not ingestion_job_id:
            raise Exception("Failed to start ingestion job")
        
        # Store job ID for polling
        ingestion_jobs[document.id] = ingestion_job_id
        
        # Start background polling task
        asyncio.create_task(poll_ingestion_status(document.id, ingestion_job_id, data_source_id))
        
        logger.info(f"Triggered ingestion for document {document.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error triggering ingestion for document {document.id}: {e}")
        document.status = DocumentStatus.ERROR
        document.error_message = f"Failed to trigger ingestion: {str(e)}"
        db.commit()
        return False


async def poll_ingestion_status(
    document_id: UUID,
    ingestion_job_id: str,
    data_source_id: str,
    max_attempts: int = 60,
    poll_interval: int = 10
):
    """Poll ingestion job status until complete or failed.
    
    Args:
        document_id: Document UUID
        ingestion_job_id: Bedrock ingestion job ID
        data_source_id: Data source ID
        max_attempts: Maximum number of polling attempts
        poll_interval: Seconds between polls
    """
    from app.database import SessionLocal
    
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        await asyncio.sleep(poll_interval)
        
        # Get job status
        status_info = get_ingestion_job_status(
            knowledge_base_id=settings.BEDROCK_KB_ID,
            data_source_id=data_source_id,
            ingestion_job_id=ingestion_job_id
        )
        
        status = status_info['status']
        
        # Update document status in database
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found during polling")
                break
            
            if status == 'COMPLETE':
                document.status = DocumentStatus.READY
                document.error_message = None
                db.commit()
                logger.info(f"Document {document_id} ingestion completed successfully")
                break
            
            elif status == 'FAILED' or status == 'ERROR':
                document.status = DocumentStatus.ERROR
                document.error_message = status_info.get('error_message', 'Ingestion failed')
                db.commit()
                logger.error(f"Document {document_id} ingestion failed: {document.error_message}")
                break
            
            elif status in ['STARTING', 'IN_PROGRESS']:
                # Continue polling
                logger.debug(f"Document {document_id} ingestion in progress (attempt {attempts}/{max_attempts})")
                continue
            
            else:
                # Unknown status
                logger.warning(f"Unknown ingestion status for document {document_id}: {status}")
                continue
                
        finally:
            db.close()
    
    # If max attempts reached
    if attempts >= max_attempts:
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document and document.status == DocumentStatus.INGESTING:
                document.status = DocumentStatus.ERROR
                document.error_message = "Ingestion timeout - exceeded maximum polling attempts"
                db.commit()
                logger.error(f"Document {document_id} ingestion timed out")
        finally:
            db.close()
    
    # Clean up job tracking
    if document_id in ingestion_jobs:
        del ingestion_jobs[document_id]


def get_ingestion_job_id(document_id: UUID) -> Optional[str]:
    """Get the ingestion job ID for a document.
    
    Args:
        document_id: Document UUID
        
    Returns:
        Ingestion job ID or None
    """
    return ingestion_jobs.get(document_id)

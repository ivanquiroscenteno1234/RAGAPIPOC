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

# Global flag to track if an ingestion job is pending/running
pending_ingestion_task: Optional[asyncio.Task] = None
ingestion_lock = asyncio.Lock()


async def trigger_ingestion(
    document: Document,
    db: Session
) -> bool:
    """Trigger ingestion for a document.
    
    Uses debouncing to prevent multiple simultaneous ingestion jobs.
    Multiple uploads within 5 seconds will be batched into a single job.
    
    Args:
        document: Document model instance
        db: Database session
        
    Returns:
        True if ingestion was triggered successfully
    """
    global pending_ingestion_task
    
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
        
        async with ingestion_lock:
            # Cancel any pending ingestion task (we'll restart it with new delay)
            if pending_ingestion_task and not pending_ingestion_task.done():
                logger.info("New upload detected, resetting ingestion delay")
                pending_ingestion_task.cancel()
            
            # Start new delayed ingestion task
            pending_ingestion_task = asyncio.create_task(_delayed_ingestion())
        
        logger.info(f"Document {document.id} queued for ingestion")
        return True
        
    except Exception as e:
        logger.error(f"Error triggering ingestion for document {document.id}: {e}")
        document.status = DocumentStatus.ERROR
        document.error_message = f"Failed to trigger ingestion: {str(e)}"
        db.commit()
        return False


async def _delayed_ingestion(delay_seconds: int = 5):
    """Wait for delay, then trigger a single ingestion job for all pending documents.
    
    Args:
        delay_seconds: Seconds to wait before starting ingestion
    """
    global pending_ingestion_task
    
    try:
        logger.info(f"Waiting {delay_seconds} seconds for more uploads...")
        await asyncio.sleep(delay_seconds)
        
        logger.info("Starting batch ingestion job...")
        
        # Trigger a single ingestion job for the entire data source
        data_source_id = settings.BEDROCK_DATA_SOURCE_ID if hasattr(settings, 'BEDROCK_DATA_SOURCE_ID') else "default-data-source"
        
        ingestion_job_id = start_ingestion_job(
            knowledge_base_id=settings.BEDROCK_KB_ID,
            data_source_id=data_source_id
        )
        
        if not ingestion_job_id:
            raise Exception("Failed to start batch ingestion job")
        
        # Start background polling task
        asyncio.create_task(_poll_batch_ingestion_status(ingestion_job_id, data_source_id))
        
        logger.info(f"Batch ingestion job started: {ingestion_job_id}")
        
    except asyncio.CancelledError:
        logger.info("Ingestion delay cancelled (new upload detected)")
        raise
    except Exception as e:
        logger.error(f"Error in delayed ingestion: {e}")
    finally:
        pending_ingestion_task = None


async def _poll_batch_ingestion_status(
    ingestion_job_id: str,
    data_source_id: str,
    max_attempts: int = 60,
    poll_interval: int = 10
):
    """Poll batch ingestion job status and update all INGESTING documents.
    
    Args:
        ingestion_job_id: Bedrock ingestion job ID
        data_source_id: Data source ID
        max_attempts: Maximum number of polling attempts
        poll_interval: Seconds between polls
    """
    from app.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            status_info = get_ingestion_job_status(
                knowledge_base_id=settings.BEDROCK_KB_ID,
                data_source_id=data_source_id,
                ingestion_job_id=ingestion_job_id
            )
            
            status = status_info['status']
            logger.info(f"Batch ingestion job {ingestion_job_id} status (attempt {attempt + 1}/{max_attempts}): {status}")
            
            if status == 'COMPLETE':
                # Update all INGESTING documents to READY
                ingesting_docs = db.query(Document).filter(
                    Document.status == DocumentStatus.INGESTING
                ).all()
                
                for doc in ingesting_docs:
                    doc.status = DocumentStatus.READY
                    doc.error_message = None
                    logger.info(f"Document {doc.id} marked as READY (batch job complete)")
                
                db.commit()
                logger.info(f"Batch ingestion complete. Updated {len(ingesting_docs)} documents.")
                return
            
            elif status == 'FAILED':
                error_msg = status_info.get('error_message', 'Unknown error')
                logger.error(f"Batch ingestion job failed: {error_msg}")
                
                # Update all INGESTING documents to ERROR
                ingesting_docs = db.query(Document).filter(
                    Document.status == DocumentStatus.INGESTING
                ).all()
                
                for doc in ingesting_docs:
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = f"Batch ingestion failed: {error_msg}"
                
                db.commit()
                return
        
        # Max attempts reached
        logger.error(f"Batch ingestion polling timeout after {max_attempts} attempts")
        ingesting_docs = db.query(Document).filter(
            Document.status == DocumentStatus.INGESTING
        ).all()
        
        for doc in ingesting_docs:
            doc.status = DocumentStatus.ERROR
            doc.error_message = "Ingestion timeout"

        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error polling batch ingestion status: {e}")
    finally:
        db.close()



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

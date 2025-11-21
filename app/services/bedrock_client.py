"""AWS Bedrock Knowledge Base client and utilities."""
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
from uuid import UUID
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Bedrock Agent client
bedrock_agent_client = boto3.client(
    'bedrock-agent',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    aws_session_token=settings.AWS_SESSION_TOKEN,
    region_name=settings.AWS_REGION
)


def start_ingestion_job(
    knowledge_base_id: str,
    data_source_id: str,
    document_id: UUID,
    user_id: UUID,
    notebook_id: UUID,
    s3_uri: str
) -> Optional[str]:
    """Start a Bedrock Knowledge Base ingestion job.
    
    Args:
        knowledge_base_id: Bedrock Knowledge Base ID
        data_source_id: Data source ID within the KB
        document_id: Document UUID
        user_id: User UUID
        notebook_id: Notebook UUID
        s3_uri: S3 URI of the document (s3://bucket/key)
        
    Returns:
        Ingestion job ID if successful, None otherwise
    """
    try:
        # Note: Bedrock KB ingestion works at the data source level
        # Metadata filtering is applied during retrieval, not ingestion
        # The actual ingestion API may vary based on your KB setup
        
        logger.info(f"Starting ingestion job - KB: {knowledge_base_id}, DS: {data_source_id}, Doc: {document_id}")
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            description=f"Ingesting document {document_id}"
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"Started ingestion job {ingestion_job_id} for document {document_id}")
        
        return ingestion_job_id
        
    except ClientError as e:
        logger.error(f"Error starting ingestion job for document {document_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error starting ingestion job: {e}")
        return None


def get_ingestion_job_status(
    knowledge_base_id: str,
    data_source_id: str,
    ingestion_job_id: str
) -> Dict[str, Any]:
    """Get the status of an ingestion job.
    
    Args:
        knowledge_base_id: Bedrock Knowledge Base ID
        data_source_id: Data source ID
        ingestion_job_id: Ingestion job ID
        
    Returns:
        Dict with status information:
        {
            'status': 'STARTING' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED',
            'error_message': str (if failed),
            'statistics': dict (if complete)
        }
    """
    try:
        response = bedrock_agent_client.get_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            ingestionJobId=ingestion_job_id
        )
        
        job = response['ingestionJob']
        status = job['status']
        
        result = {
            'status': status,
            'error_message': None,
            'statistics': None
        }
        
        if status == 'FAILED':
            failure_reasons = job.get('failureReasons', [])
            result['error_message'] = '; '.join(failure_reasons) if failure_reasons else 'Unknown error'
        
        if status == 'COMPLETE':
            result['statistics'] = job.get('statistics', {})
        
        logger.info(f"Ingestion job {ingestion_job_id} status: {status}")
        return result
        
    except ClientError as e:
        logger.error(f"Error getting ingestion job status: {e}")
        return {
            'status': 'ERROR',
            'error_message': str(e),
            'statistics': None
        }
    except Exception as e:
        logger.error(f"Unexpected error getting ingestion job status: {e}")
        return {
            'status': 'ERROR',
            'error_message': str(e),
            'statistics': None
        }


def create_metadata_filter(
    user_id: UUID,
    notebook_id: UUID,
    document_ids: Optional[list[UUID]] = None
) -> Dict[str, Any]:
    """Create metadata filter for retrieval.
    
    This filter ensures multi-tenancy isolation during retrieval.
    
    Args:
        user_id: User UUID
        notebook_id: Notebook UUID
        document_ids: Optional list of specific document IDs to filter
        
    Returns:
        Metadata filter dict for Bedrock KB retrieval
    """
    # Build filter with AND conditions
    filters = [
        {
            "equals": {
                "key": "user_id",
                "value": str(user_id)
            }
        },
        {
            "equals": {
                "key": "notebook_id",
                "value": str(notebook_id)
            }
        }
    ]
    
    # Add document filter if specified
    if document_ids:
        filters.append({
            "in": {
                "key": "document_id",
                "value": [str(doc_id) for doc_id in document_ids]
            }
        })
    
    return {
        "andAll": filters
    }

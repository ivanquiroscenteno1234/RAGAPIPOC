"""AWS S3 client configuration and utilities."""
import boto3
from botocore.exceptions import ClientError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize S3 client lazily to avoid errors with empty credentials
_s3_client = None

def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None and settings.AWS_ACCESS_KEY_ID:
        _s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN,
            region_name=settings.AWS_REGION
        )
    return _s3_client


def upload_file_to_s3(file_content: bytes, s3_key: str, content_type: str = None) -> bool:
    """Upload a file to S3.
    
    Args:
        file_content: File content as bytes
        s3_key: S3 object key (path)
        content_type: MIME type of the file
        
    Returns:
        True if successful, False otherwise
    """
    # Check if AWS credentials are configured
    if not settings.AWS_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
        logger.warning(f"AWS credentials not configured. Skipping S3 upload for: {s3_key}")
        logger.info("File upload mocked successfully (no S3 storage)")
        return True
    
    try:
        s3_client = get_s3_client()
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            **extra_args
        )
        logger.info(f"Successfully uploaded file to S3: {s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error uploading file to S3: {e}")
        return False


def delete_file_from_s3(s3_key: str) -> bool:
    """Delete a file from S3.
    
    Args:
        s3_key: S3 object key (path)
        
    Returns:
        True if successful, False otherwise
    """
    # Check if AWS credentials are configured
    if not settings.AWS_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
        logger.warning(f"AWS credentials not configured. Skipping S3 delete for: {s3_key}")
        logger.info("File deletion mocked successfully (no S3 storage)")
        return True
    
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key
        )
        logger.info(f"Successfully deleted file from S3: {s3_key}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting file from S3: {e}")
        return False


def get_file_from_s3(s3_key: str) -> bytes | None:
    """Get a file from S3.
    
    Args:
        s3_key: S3 object key (path)
        
    Returns:
        File content as bytes, or None if error
    """
    try:
        s3_client = get_s3_client()
        if not s3_client:
            return None
        response = s3_client.get_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Error getting file from S3: {e}")
        return None

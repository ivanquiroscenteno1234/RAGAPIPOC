"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Components
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = "5432"
    DB_NAME: Optional[str] = "postgres"
    
    # Database URL (can be provided directly or constructed)
    DATABASE_URL: Optional[str] = None
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    BEDROCK_KB_ID: Optional[str] = None
    BEDROCK_DATA_SOURCE_ID: Optional[str] = None
    
    # Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-pro"
    
    # Application
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        """Construct DATABASE_URL if not provided."""
        if not self.DATABASE_URL and self.DB_USER and self.DB_PASSWORD and self.DB_HOST:
            encoded_password = quote_plus(self.DB_PASSWORD)
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return self
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Global settings instance
settings = Settings()


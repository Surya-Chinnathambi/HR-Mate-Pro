from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field
import os
from pathlib import Path

# Get the base directory (hrms_backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "HRMS Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/hrms_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OpenAI / Azure OpenAI
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    AZURE_OPENAI_ENDPOINT: str = Field(default="", description="Azure OpenAI Endpoint")
    AZURE_OPENAI_KEY: str = Field(default="", description="Azure OpenAI API Key")
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = str(ENV_FILE)  # Use absolute path to .env file
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()
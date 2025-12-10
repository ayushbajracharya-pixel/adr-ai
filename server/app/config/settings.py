from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """

    # OpenAPI
    OPENAI_API_KEY: str

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://adr_user:adr_password@postgres:5432/adr_db"

    # ChromaDB
    CHROMADB_HOST: str = "chromadb"  # Use "localhost" when running locally, "chromadb" in Docker
    CHROMADB_PORT: int = 8000  # Use 8001 when running locally (host port), 8000 in Docker (container port)

    # AWS / LocalStack
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    S3_BUCKET_NAME: str
    S3_BUCKET_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = None  # For LocalStack: http://localstack:4566

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    SECRET_KEY: str  # Secret key for session signing (generate a random string)
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend URL for OAuth redirect

    # LangSmith
    LANGCHAIN_TRACING_V2: Optional[str] = None  # Set to "true" to enable
    LANGCHAIN_ENDPOINT: Optional[str] = None  # LangSmith API endpoint
    LANGCHAIN_API_KEY: Optional[str] = None  # LangSmith API key
    LANGCHAIN_PROJECT: Optional[str] = None  # LangSmith project name

    class Config:
        env_file = ".env"  # Specifies the name of the .env file


settings = Settings()

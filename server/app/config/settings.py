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

    # LLM Configuration
    LLM_MODEL_NAME: str = "gpt-4.1-nano"  # Model name for query generation
    LLM_TEMPERATURE: float = 0.1  # Temperature for query generation LLM
    EXTRACTION_MODEL_NAME: str = "gpt-4.1-nano"  # Model name for extraction chains
    EXTRACTION_TEMPERATURE: float = 0.0  # Temperature for extraction chains

    # Retrieval Configuration
    RETRIEVAL_K: int = 5  # Number of documents to retrieve
    RETRIEVAL_SEARCH_TYPE: str = "similarity"  # Search type for retrieval

    # Text Splitting Configuration
    CHUNK_SIZE: int = 1000  # Character size for document chunks
    CHUNK_OVERLAP: int = 200  # Character overlap between chunks

    # Conversation History Configuration
    CONVERSATION_HISTORY_LIMIT: int = 10  # Max messages to include in prompt
    MESSAGE_TRUNCATE_LENGTH: int = 500  # Max characters per message in prompt
    MAX_RECENT_MESSAGES: int = 4  # Max recent messages for query validation
    MESSAGE_PREVIEW_LENGTH: int = 200  # Max characters for message preview in validation

    class Config:
        env_file = ".env"  # Specifies the name of the .env file


settings = Settings()

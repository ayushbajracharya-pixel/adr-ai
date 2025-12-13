"""Custom exception classes for the application."""
from fastapi import HTTPException, status


class ADRException(HTTPException):
    """Base exception for ADR-related errors."""
    pass


class FileProcessingError(ADRException):
    """Raised when file processing fails."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class VectorStoreError(ADRException):
    """Raised when vector store operations fail."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class StorageError(ADRException):
    """Raised when storage operations fail."""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


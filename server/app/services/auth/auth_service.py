"""Authentication service for JWT token management."""
from typing import Optional
from datetime import datetime, timedelta
from app.core.security import create_access_token, verify_token

ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    return create_access_token(data, expires_delta)


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    return verify_token(token)


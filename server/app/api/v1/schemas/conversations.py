"""Conversation-related schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from app.domain.schemas.query import Reference


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    user_email: str
    title: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    references: Optional[List[Reference]] = None
    created_at: str

    class Config:
        from_attributes = True


class ConversationWithMessages(BaseModel):
    id: str
    user_email: str
    title: Optional[str]
    created_at: str
    updated_at: str
    messages: List[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


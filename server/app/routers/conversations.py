from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.config.database import get_db
from app.routers.auth import get_current_user
from app.services.conversation_service import ConversationService
from app.models.schemas import QueryRequest, QueryResponse, Reference
from app.services.adr_service import ADRService
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

conversation_service = ConversationService()
adr_service = ADRService()


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


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation"""
    conversation = await conversation_service.create_conversation(
        db, current_user["email"], conversation_data.title
    )
    await db.commit()
    return conversation.to_dict()


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """List all conversations for the current user"""
    conversations = await conversation_service.list_conversations(
        db, current_user["email"], limit
    )
    return [conv.to_dict() for conv in conversations]


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all its messages"""
    result = await conversation_service.get_conversation_with_messages(
        db, conversation_id, current_user["email"]
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    
    return {
        **result["conversation"].to_dict(),
        "messages": [msg.to_dict() for msg in result["messages"]],
    }


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update conversation title"""
    conversation = await conversation_service.update_conversation_title(
        db, conversation_id, current_user["email"], conversation_data.title
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    await db.commit()
    return conversation.to_dict()


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages"""
    deleted = await conversation_service.delete_conversation(
        db, conversation_id, current_user["email"]
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    await db.commit()
    return None


@router.post("/{conversation_id}/messages", response_model=QueryResponse)
async def send_message(
    conversation_id: str,
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a conversation and get AI response"""
    # Verify conversation exists and belongs to user
    conversation = await conversation_service.get_conversation(
        db, conversation_id, current_user["email"]
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Get conversation history
    messages = await conversation_service.get_messages(db, conversation_id)
    conversation_history = [
        {"role": msg.role, "content": msg.content} for msg in messages
    ]

    # Save user message
    user_message = await conversation_service.add_message(
        db, conversation_id, "user", request.query
    )

    # Generate title from first message if not set
    if not conversation.title or conversation.title == "New Conversation":
        # Use first 50 chars of first user message as title
        title = request.query[:50] + ("..." if len(request.query) > 50 else "")
        conversation.title = title

    # Query ADR service with conversation history
    try:
        response = await adr_service.query_adr(request.query, conversation_history)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Save assistant response
    assistant_message = await conversation_service.add_message(
        db,
        conversation_id,
        "assistant",
        response["response"],
        references=response.get("references"),
    )

    await db.commit()

    return {
        "query": request.query,
        "response": response["response"],
        "references": response.get("references", []),
    }


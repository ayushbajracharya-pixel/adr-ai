from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.database import Conversation, Message
from datetime import datetime


class ConversationService:
    """Service for managing conversations and messages"""

    async def create_conversation(
        self, db: AsyncSession, user_email: str, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            user_email=user_email,
            title=title or "New Conversation",
        )
        db.add(conversation)
        await db.flush()
        return conversation

    async def get_conversation(
        self, db: AsyncSession, conversation_id: str, user_email: str
    ) -> Optional[Conversation]:
        """Get a conversation by ID, ensuring it belongs to the user"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_email == user_email,
            )
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self, db: AsyncSession, user_email: str, limit: int = 50
    ) -> List[Conversation]:
        """List all conversations for a user"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_email == user_email)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_conversation_title(
        self, db: AsyncSession, conversation_id: str, user_email: str, title: str
    ) -> Optional[Conversation]:
        """Update conversation title"""
        conversation = await self.get_conversation(db, conversation_id, user_email)
        if conversation:
            conversation.title = title
            await db.flush()
        return conversation

    async def delete_conversation(
        self, db: AsyncSession, conversation_id: str, user_email: str
    ) -> bool:
        """Delete a conversation and all its messages"""
        conversation = await self.get_conversation(db, conversation_id, user_email)
        if conversation:
            await db.delete(conversation)
            await db.flush()
            return True
        return False

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        references: Optional[dict] = None,
    ) -> Message:
        """Add a message to a conversation"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            references=references,
        )
        db.add(message)
        await db.flush()
        return message

    async def get_messages(
        self, db: AsyncSession, conversation_id: str, limit: int = 100
    ) -> List[Message]:
        """Get all messages for a conversation"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_conversation_with_messages(
        self, db: AsyncSession, conversation_id: str, user_email: str
    ) -> Optional[dict]:
        """Get a conversation with all its messages"""
        conversation = await self.get_conversation(db, conversation_id, user_email)
        if conversation:
            messages = await self.get_messages(db, conversation_id)
            return {
                "conversation": conversation,
                "messages": messages,
            }
        return None


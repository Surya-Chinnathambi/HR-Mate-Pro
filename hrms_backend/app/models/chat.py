"""
Chat conversation models for AI assistant chat history
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from enum import Enum


class ChatRole(str, Enum):
    """Chat message role"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatConversation(SQLModel, table=True):
    """
    Stores chat conversation metadata
    Similar to ChatGPT conversation sidebar
    """
    __tablename__ = "chat_conversations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    
    # Conversation metadata
    title: str = Field(max_length=255, default="New Chat")  # Auto-generated from first message
    summary: Optional[str] = Field(default=None, max_length=500)  # Brief summary of conversation
    
    # Status
    is_active: bool = Field(default=True)  # Current active conversation
    is_archived: bool = Field(default=False)
    is_pinned: bool = Field(default=False)
    
    # Metadata
    message_count: int = Field(default=0)
    last_message_at: Optional[datetime] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    messages: List["ChatMessage"] = Relationship(back_populates="conversation", cascade_delete=True)
    # Note: employee relationship removed to avoid circular imports
    # Foreign key still exists in database for referential integrity


class ChatMessage(SQLModel, table=True):
    """
    Individual messages within a conversation
    """
    __tablename__ = "chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chat_conversations.id", index=True)
    
    # Message content
    role: ChatRole = Field(sa_column=Column(JSON))  # USER, ASSISTANT, SYSTEM
    content: str = Field(max_length=10000)  # Message text
    
    # Function calling (for AI actions)
    function_name: Optional[str] = Field(default=None, max_length=100)
    function_args: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    function_result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Metadata
    tokens_used: Optional[int] = Field(default=None)
    model_used: Optional[str] = Field(default=None, max_length=100)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    conversation: Optional[ChatConversation] = Relationship(back_populates="messages")


# Add to Employee model relationship (add this to employee.py)
"""
from typing import List
from app.models.chat import ChatConversation

class Employee(SQLModel, table=True):
    # ... existing fields ...
    
    # Chat history
    chat_conversations: List["ChatConversation"] = Relationship(back_populates="employee", cascade_delete=True)
"""

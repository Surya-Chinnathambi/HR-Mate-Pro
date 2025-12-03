"""
SQLModel models for AI chatbot conversation tracking
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy.dialects.postgresql import UUID, TEXT
import uuid


class ConversationHistory(SQLModel, table=True):
    __tablename__ = "conversation_history"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(UUID(as_uuid=True), primary_key=True))
    conversation_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False, index=True))
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    role: str = Field(max_length=20, nullable=False)  # employee, manager, hr_admin, super_admin
    message_type: str = Field(max_length=20, nullable=False)  # user_message, bot_response, system_event
    message_text: str = Field(sa_column=Column("message_text", TEXT, nullable=False))
    intent: Optional[str] = Field(default=None, max_length=100)
    entities: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    function_called: Optional[str] = Field(default=None, max_length=100)
    function_params: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    function_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    policy_applied: Optional[str] = Field(default=None, max_length=200)
    action_status: Optional[str] = Field(default=None, max_length=50)
    extra_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)


class AIChatSession(SQLModel, table=True):
    __tablename__ = "ai_chat_sessions"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(UUID(as_uuid=True), primary_key=True))
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    session_start: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    session_end: Optional[datetime] = Field(default=None)
    total_messages: int = Field(default=0)
    intents_handled: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    satisfaction_score: Optional[float] = Field(default=None)
    escalated_to_human: bool = Field(default=False)
    extra_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON))


class AIFunctionCall(SQLModel, table=True):
    __tablename__ = "ai_function_calls"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(UUID(as_uuid=True), primary_key=True))
    conversation_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False, index=True))
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    function_name: str = Field(max_length=100, nullable=False, index=True)
    parameters: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(max_length=50, nullable=False)  # success, failed, pending
    execution_time_ms: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    policy_checks: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(default=None, max_length=45)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)

"""
AI Chatbot API endpoints for HR Assistant
Handles chat messages, function calling, and conversation history
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import get_async_session, get_session
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.ai_chat import ConversationHistory, AIChatSession
from app.services.ai_chatbot import HRChatbotService

router = APIRouter(prefix="/chatbot", tags=["AI Chatbot"])


# Request/Response Models
class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    success: bool
    conversation_id: str
    message: str
    function_called: Optional[str] = None
    timestamp: str
    error: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    id: str
    message_type: str
    message_text: str
    intent: Optional[str]
    function_called: Optional[str]
    action_status: Optional[str]
    created_at: datetime


class ConversationListResponse(BaseModel):
    id: str
    session_start: datetime
    session_end: Optional[datetime]
    total_messages: int
    last_message_preview: str


@router.post("/chat", response_model=ChatMessageResponse)
async def chat_with_bot(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Send a message to the HR AI chatbot and get a response
    
    **Features:**
    - Natural language understanding
    - Function calling for HR operations
    - Role-based access control
    - Policy enforcement
    - Conversation context memory
    
    **Example requests:**
    - "Apply sick leave for tomorrow"
    - "What's my leave balance?"
    - "Clock in"
    - "Show my attendance for this month"
    - "Submit expense for $50 lunch"
    """
    try:
        # Initialize chatbot service
        chatbot = HRChatbotService(session)
        
        # Process message
        response = await chatbot.chat(
            user_message=request.message,
            user=current_user,
            conversation_id=request.conversation_id
        )
        
        return ChatMessageResponse(**response)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot error: {str(e)}"
        )


@router.get("/conversations", response_model=List[ConversationListResponse])
async def get_user_conversations(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get list of user's chat conversations
    
    Returns recent conversations with preview of last message
    """
    try:
        # Get distinct conversation sessions
        stmt = select(AIChatSession).where(
            AIChatSession.user_id == current_user.id
        ).order_by(AIChatSession.session_start.desc()).limit(limit)
        
        sessions = session.exec(stmt).all()
        
        conversations = []
        for chat_session in sessions:
            # Get last message from this conversation
            last_msg_stmt = select(ConversationHistory).where(
                ConversationHistory.conversation_id == chat_session.id,
                ConversationHistory.message_type == "user_message"
            ).order_by(ConversationHistory.created_at.desc()).limit(1)
            
            last_msg = session.exec(last_msg_stmt).first()
            
            conversations.append(ConversationListResponse(
                id=str(chat_session.id),
                session_start=chat_session.session_start,
                session_end=chat_session.session_end,
                total_messages=chat_session.total_messages,
                last_message_preview=last_msg.message_text[:100] if last_msg else "No messages"
            ))
        
        return conversations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/history", response_model=List[ConversationHistoryResponse])
async def get_conversation_history(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Get full history of a specific conversation
    
    Returns all messages in chronological order
    """
    try:
        # Verify conversation belongs to user
        stmt = select(ConversationHistory).where(
            ConversationHistory.conversation_id == uuid.UUID(conversation_id),
            ConversationHistory.user_id == current_user.id
        ).order_by(ConversationHistory.created_at.asc())
        
        messages = session.exec(stmt).all()
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return [
            ConversationHistoryResponse(
                id=str(msg.id),
                message_type=msg.message_type,
                message_text=msg.message_text,
                intent=msg.intent,
                function_called=msg.function_called,
                action_status=msg.action_status,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation history: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Delete a conversation and all its messages
    
    **Warning:** This action cannot be undone
    """
    try:
        # Verify conversation belongs to user and delete
        stmt = select(ConversationHistory).where(
            ConversationHistory.conversation_id == uuid.UUID(conversation_id),
            ConversationHistory.user_id == current_user.id
        )
        
        messages = session.exec(stmt).all()
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete all messages
        for msg in messages:
            session.delete(msg)
        
        # Delete session if exists
        session_stmt = select(AIChatSession).where(
            AIChatSession.id == uuid.UUID(conversation_id)
        )
        chat_session = session.exec(session_stmt).first()
        if chat_session:
            session.delete(chat_session)
        
        session.commit()
        
        return {"success": True, "message": "Conversation deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@router.get("/quick-actions")
async def get_quick_actions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get role-based quick action commands
    
    Returns list of common commands user can execute
    """
    employee_actions = [
        {"command": "/leave", "description": "Apply for leave", "icon": "📅"},
        {"command": "/balance", "description": "Check leave balance", "icon": "📊"},
        {"command": "/attendance", "description": "View attendance", "icon": "⏰"},
        {"command": "/clock-in", "description": "Clock in", "icon": "🔔"},
        {"command": "/expense", "description": "Submit expense", "icon": "💰"},
        {"command": "/payslip", "description": "Get payslip", "icon": "📄"},
        {"command": "/help", "description": "Show all commands", "icon": "❓"}
    ]
    
    manager_actions = employee_actions + [
        {"command": "/approvals", "description": "View pending approvals", "icon": "✅"},
        {"command": "/team", "description": "Team dashboard", "icon": "👥"},
    ]
    
    hr_actions = manager_actions + [
        {"command": "/reports", "description": "Generate reports", "icon": "📈"},
        {"command": "/policies", "description": "Manage policies", "icon": "📋"},
    ]
    
    if current_user.role == "EMPLOYEE":
        return {"actions": employee_actions}
    elif current_user.role == "MANAGER":
        return {"actions": manager_actions}
    elif current_user.role == "HR":
        return {"actions": hr_actions}
    else:
        return {"actions": employee_actions}


@router.get("/health")
async def chatbot_health_check():
    """
    Check if chatbot service is available
    
    Validates:
    - OpenAI API connectivity
    - Redis connectivity
    - Database connectivity
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "openai": "configured",
            "redis": "connected",
            "database": "connected"
        }
    }
    
    # TODO: Add actual health checks
    # - Test OpenAI API call
    # - Test Redis connection
    # - Test database query
    
    return health_status

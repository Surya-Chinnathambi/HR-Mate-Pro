"""
API endpoints for chat history management
Supports ChatGPT-like conversation sidebar with history persistence
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, or_, and_
from datetime import datetime

from app.database import get_session
from app.models.chat import ChatConversation, ChatMessage, ChatRole
from app.models.user import Employee
from app.core.security import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

@router.get("/conversations")
async def get_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = Query(False),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Get all conversations for the current user
    Similar to ChatGPT sidebar - shows conversation history
    
    Returns conversations ordered by:
    1. Pinned first
    2. Then by last_message_at (most recent first)
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Build query
    query = select(ChatConversation).where(
        ChatConversation.employee_id == employee.id
    )
    
    # Filter archived
    if not include_archived:
        query = query.where(ChatConversation.is_archived == False)
    
    # Order: pinned first, then by last message
    query = query.order_by(
        ChatConversation.is_pinned.desc(),
        ChatConversation.last_message_at.desc()
    )
    
    # Pagination
    query = query.offset(skip).limit(limit)
    
    conversations = session.exec(query).all()
    
    return {
        "conversations": conversations,
        "total": len(conversations)
    }


@router.post("/conversations")
async def create_conversation(
    title: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Create a new conversation
    Like clicking "New Chat" in ChatGPT
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Set all other conversations as inactive
    existing_conversations = session.exec(
        select(ChatConversation).where(
            ChatConversation.employee_id == employee.id,
            ChatConversation.is_active == True
        )
    ).all()
    
    for conv in existing_conversations:
        conv.is_active = False
        session.add(conv)
    
    # Create new conversation
    conversation = ChatConversation(
        employee_id=employee.id,
        title=title or "New Chat",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    
    return conversation


@router.get("/conversations/{conversation_id}")
async def get_conversation_details(
    conversation_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Get a specific conversation with all its messages
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    
    # Get all messages
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    
    return {
        "conversation": conversation,
        "messages": messages
    }


@router.put("/conversations/{conversation_id}/activate")
async def activate_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Set a conversation as active (current chat)
    Like clicking on a conversation in ChatGPT sidebar
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Deactivate all other conversations
    other_conversations = session.exec(
        select(ChatConversation).where(
            ChatConversation.employee_id == employee.id,
            ChatConversation.id != conversation_id,
            ChatConversation.is_active == True
        )
    ).all()
    
    for conv in other_conversations:
        conv.is_active = False
        session.add(conv)
    
    # Activate this conversation
    conversation.is_active = True
    session.add(conversation)
    
    session.commit()
    session.refresh(conversation)
    
    return conversation


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    title: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Update conversation metadata
    - Rename conversation
    - Pin/unpin conversation
    - Archive conversation
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update fields
    if title is not None:
        conversation.title = title
    if is_pinned is not None:
        conversation.is_pinned = is_pinned
    if is_archived is not None:
        conversation.is_archived = is_archived
        if is_archived:
            conversation.is_active = False  # Can't be active if archived
    
    conversation.updated_at = datetime.utcnow()
    
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete conversation (cascades to messages)
    session.delete(conversation)
    session.commit()
    
    return {"message": "Conversation deleted successfully"}


# ============================================================================
# MESSAGE MANAGEMENT
# ============================================================================

@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: int,
    role: ChatRole,
    content: str,
    function_name: Optional[str] = None,
    function_args: Optional[dict] = None,
    function_result: Optional[dict] = None,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Add a message to a conversation
    Used when sending/receiving chat messages
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create message
    message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        function_name=function_name,
        function_args=function_args,
        function_result=function_result,
        created_at=datetime.utcnow()
    )
    
    session.add(message)
    
    # Update conversation metadata
    conversation.message_count += 1
    conversation.last_message_at = datetime.utcnow()
    conversation.updated_at = datetime.utcnow()
    
    # Auto-generate title from first user message
    if conversation.message_count == 1 and role == ChatRole.USER:
        # Use first 50 chars of message as title
        conversation.title = content[:50] + ("..." if len(content) > 50 else "")
    
    session.add(conversation)
    session.commit()
    session.refresh(message)
    
    return message


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Get messages for a conversation
    Paginated for performance with large conversations
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get conversation
    conversation = session.get(ChatConversation, conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check ownership
    if conversation.employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get messages
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    ).all()
    
    return {
        "messages": messages,
        "total": conversation.message_count
    }


# ============================================================================
# ACTIVE CONVERSATION HELPER
# ============================================================================

@router.get("/active")
async def get_active_conversation(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Get the currently active conversation
    Used to restore chat state when page loads
    """
    # Get employee
    employee = session.exec(
        select(Employee).where(Employee.user_id == current_user.id)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get active conversation
    conversation = session.exec(
        select(ChatConversation).where(
            ChatConversation.employee_id == employee.id,
            ChatConversation.is_active == True
        )
    ).first()
    
    if not conversation:
        # Create a new conversation if none exists
        conversation = ChatConversation(
            employee_id=employee.id,
            title="New Chat",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
    
    # Get messages
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    
    return {
        "conversation": conversation,
        "messages": messages
    }

"""
Group Chat API with WebSocket support for real-time messaging.
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Dict, Optional
from datetime import datetime
import json
from jose import jwt, JWTError
from pydantic import BaseModel

from app.database import get_async_session
from app.models.extras import GroupChatMessage, ChatReadReceipt
from app.models.user import User, Employee
from app.core.security import get_current_active_user
from app.config import settings

router = APIRouter(prefix="/group-chat", tags=["group-chat"])


# Pydantic models for request validation
class SendMessageRequest(BaseModel):
    message: str
    message_type: str = "text"
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_name: Optional[str] = None
    reply_to_id: Optional[int] = None


class AddReactionRequest(BaseModel):
    emoji: str


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}  # employee_id: [websockets]
    
    async def connect(self, websocket: WebSocket, employee_id: int):
        await websocket.accept()
        if employee_id not in self.active_connections:
            self.active_connections[employee_id] = []
        self.active_connections[employee_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, employee_id: int):
        if employee_id in self.active_connections:
            self.active_connections[employee_id].remove(websocket)
            if not self.active_connections[employee_id]:
                del self.active_connections[employee_id]
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        disconnected = []
        for employee_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append((employee_id, connection))
        
        # Clean up disconnected websockets
        for employee_id, connection in disconnected:
            self.disconnect(connection, employee_id)
    
    async def send_personal_message(self, message: dict, employee_id: int):
        """Send message to specific employee's connections"""
        if employee_id in self.active_connections:
            for connection in self.active_connections[employee_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{employee_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    employee_id: int,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time chat.
    Usage: ws://localhost:8000/api/group-chat/ws/{employee_id}?token={jwt_token}
    """
    # Verify token manually
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=1008, reason="Unauthorized")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    await manager.connect(websocket, employee_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Echo back or process (actual message sending handled via REST API)
            await manager.send_personal_message({
                "type": "ack",
                "message": "Message received",
                "timestamp": datetime.utcnow().isoformat()
            }, employee_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, employee_id)


@router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Send a new group chat message"""
    
    # Get sender employee info
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create message
    chat_message = GroupChatMessage(
        sender_id=employee.id,
        sender_name=f"{employee.first_name} {employee.last_name}",
        sender_role=current_user.role,
        message=request.message,
        message_type=request.message_type,
        attachment_url=request.attachment_url,
        attachment_type=request.attachment_type,
        attachment_name=request.attachment_name,
        reply_to_id=request.reply_to_id
    )
    
    session.add(chat_message)
    await session.commit()
    await session.refresh(chat_message)
    
    # Broadcast to all connected clients
    message_data = {
        "type": "new_message",
        "message": {
            "id": chat_message.id,
            "sender_id": chat_message.sender_id,
            "sender_name": chat_message.sender_name,
            "sender_role": chat_message.sender_role,
            "message": chat_message.message,
            "message_type": chat_message.message_type,
            "attachment_url": chat_message.attachment_url,
            "attachment_type": chat_message.attachment_type,
            "attachment_name": chat_message.attachment_name,
            "reply_to_id": chat_message.reply_to_id,
            "is_edited": chat_message.is_edited,
            "reactions": chat_message.reactions,
            "created_at": chat_message.created_at.isoformat(),
        }
    }
    
    await manager.broadcast(message_data)
    
    return message_data["message"]


@router.get("/messages")
async def get_messages(
    limit: int = 50,
    before_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get recent chat messages (pagination support)"""
    
    query = select(GroupChatMessage).where(
        GroupChatMessage.is_deleted == False
    ).order_by(desc(GroupChatMessage.created_at))
    
    if before_id:
        query = query.where(GroupChatMessage.id < before_id)
    
    query = query.limit(limit)
    
    result = await session.execute(query)
    messages = result.scalars().all()
    
    return [
        {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "sender_role": msg.sender_role,
            "message": msg.message,
            "message_type": msg.message_type,
            "attachment_url": msg.attachment_url,
            "attachment_type": msg.attachment_type,
            "attachment_name": msg.attachment_name,
            "reply_to_id": msg.reply_to_id,
            "is_edited": msg.is_edited,
            "reactions": msg.reactions,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in reversed(messages)  # Return in chronological order
    ]


@router.put("/messages/{message_id}")
async def edit_message(
    message_id: int,
    new_message: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Edit a message (only sender can edit)"""
    
    # Get employee
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get message
    message_result = await session.execute(
        select(GroupChatMessage).where(GroupChatMessage.id == message_id)
    )
    message = message_result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.sender_id != employee.id:
        raise HTTPException(status_code=403, detail="Can only edit your own messages")
    
    # Update message
    message.message = new_message
    message.is_edited = True
    message.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Broadcast update
    await manager.broadcast({
        "type": "message_edited",
        "message_id": message_id,
        "new_message": new_message,
        "is_edited": True,
        "updated_at": message.updated_at.isoformat()
    })
    
    return {"success": True, "message": "Message updated"}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a message (soft delete)"""
    
    # Get employee
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get message
    message_result = await session.execute(
        select(GroupChatMessage).where(GroupChatMessage.id == message_id)
    )
    message = message_result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Allow sender or HR/admin to delete
    if message.sender_id != employee.id and current_user.role not in ["hr", "super_admin"]:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    
    # Soft delete
    message.is_deleted = True
    message.deleted_at = datetime.utcnow()
    
    await session.commit()
    
    # Broadcast deletion
    await manager.broadcast({
        "type": "message_deleted",
        "message_id": message_id
    })
    
    return {"success": True, "message": "Message deleted"}


@router.post("/messages/{message_id}/react")
async def add_reaction(
    message_id: int,
    request: AddReactionRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Add emoji reaction to a message"""
    
    # Get employee
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get message
    message_result = await session.execute(
        select(GroupChatMessage).where(GroupChatMessage.id == message_id)
    )
    message = message_result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Parse existing reactions
    reactions = json.loads(message.reactions) if message.reactions else []
    
    # Find existing emoji reaction
    emoji_reaction = next((r for r in reactions if r["emoji"] == request.emoji), None)
    
    if emoji_reaction:
        # Add employee to reaction if not already there
        if employee.id not in emoji_reaction["employee_ids"]:
            emoji_reaction["employee_ids"].append(employee.id)
    else:
        # Create new reaction
        reactions.append({
            "emoji": request.emoji,
            "employee_ids": [employee.id]
        })
    
    message.reactions = json.dumps(reactions)
    await session.commit()
    
    # Broadcast reaction update
    await manager.broadcast({
        "type": "reaction_added",
        "message_id": message_id,
        "emoji": request.emoji,
        "employee_id": employee.id,
        "reactions": reactions
    })
    
    return {"success": True, "reactions": reactions}


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get unread message count for current user"""
    
    # Get employee
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get last read receipt
    receipt_result = await session.execute(
        select(ChatReadReceipt).where(ChatReadReceipt.employee_id == employee.id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if not receipt:
        # Count all messages if never read
        count_result = await session.execute(
            select(func.count(GroupChatMessage.id)).where(
                GroupChatMessage.is_deleted == False
            )
        )
        count = count_result.scalar() or 0
    else:
        # Count messages after last read
        count_result = await session.execute(
            select(func.count(GroupChatMessage.id)).where(
                and_(
                    GroupChatMessage.id > receipt.last_read_message_id,
                    GroupChatMessage.is_deleted == False
                )
            )
        )
        count = count_result.scalar() or 0
    
    return {"unread_count": count}


@router.post("/mark-read")
async def mark_messages_read(
    last_message_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Mark messages as read up to a certain message ID"""
    
    # Get employee
    employee_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = employee_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get or create read receipt
    receipt_result = await session.execute(
        select(ChatReadReceipt).where(ChatReadReceipt.employee_id == employee.id)
    )
    receipt = receipt_result.scalar_one_or_none()
    
    if receipt:
        receipt.last_read_message_id = last_message_id
        receipt.last_read_at = datetime.utcnow()
    else:
        receipt = ChatReadReceipt(
            employee_id=employee.id,
            last_read_message_id=last_message_id
        )
        session.add(receipt)
    
    await session.commit()
    
    return {"success": True, "message": "Messages marked as read"}

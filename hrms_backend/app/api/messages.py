"""
Messages API
Direct messaging between employees with audit logging
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_async_session
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.notification_delivery import NotificationDeliveryService

router = APIRouter(prefix="/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    recipient_employee_id: int
    subject: str
    body: str
    priority: Optional[str] = "normal"  # low, normal, high, urgent


@router.post("/send")
async def send_message(
    message_data: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Send a direct message to another employee
    
    Creates message record and inbox notification
    Emits event via pg_notify for real-time delivery
    """
    try:
        # Get sender's employee_id
        sender_query = text("""
            SELECT id, first_name, last_name FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(sender_query, {"user_id": current_user.id})
        sender = result.fetchone()
        
        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sender employee profile not found"
            )
        
        sender_employee_id = sender[0]
        sender_name = f"{sender[1]} {sender[2]}"
        
        # Verify recipient exists
        recipient_query = text("""
            SELECT id, first_name, last_name FROM employees WHERE id = :employee_id
        """)
        result = await db.execute(recipient_query, {
            "employee_id": message_data.recipient_employee_id
        })
        recipient = result.fetchone()
        
        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient employee not found"
            )
        
        recipient_name = f"{recipient[1]} {recipient[2]}"
        
        # Create message record
        message_insert = text("""
            INSERT INTO messages (
                sender_employee_id,
                body,
                created_at
            ) VALUES (
                :sender_employee_id,
                :body,
                NOW()
            )
            RETURNING id, created_at
        """)
        
        result = await db.execute(message_insert, {
            "sender_employee_id": sender_employee_id,
            "body": f"Subject: {message_data.subject}\n\n{message_data.body}"
        })
        message_row = result.fetchone()
        message_id = message_row[0]
        
        # Create inbox notification using NotificationDeliveryService
        inbox_ids = await NotificationDeliveryService.create_inbox_notification(
            db=db,
            recipient_employee_ids=[message_data.recipient_employee_id],
            notification_type="message_received",
            message_id=message_id,
            entity_type="message",
            entity_id=message_id,
            title=f"New message from {sender_name}",
            body=f"{message_data.subject[:100]}...",
            metadata={
                "sender_employee_id": sender_employee_id,
                "sender_name": sender_name,
                "subject": message_data.subject,
                "priority": message_data.priority
            }
        )
        
        # Create audit log
        from app.models.workflow import AuditLog, AuditAction
        
        audit_log = AuditLog(
            user_id=current_user.id,
            employee_id=sender_employee_id,
            action=AuditAction.SEND_MESSAGE,
            entity_type="message",
            entity_id=message_id,
            description=f"Sent message to {recipient_name}: {message_data.subject}",
            new_value={
                "recipient_employee_id": message_data.recipient_employee_id,
                "subject": message_data.subject,
                "priority": message_data.priority
            },
            success=True
        )
        db.add(audit_log)
        
        await db.commit()
        
        # Build delivery status
        delivery_status = NotificationDeliveryService.build_delivery_status(
            entity_created=True,
            inbox_created=len(inbox_ids) > 0,
            event_emitted=True,
            audit_logged=True,
            event_channel="messages_events",
            inbox_ids=inbox_ids,
            error=None
        )
        
        return {
            "success": True,
            "message": "Message sent successfully",
            "message_id": message_id,
            "recipient": {
                "employee_id": message_data.recipient_employee_id,
                "name": recipient_name
            },
            "delivery_status": delivery_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error sending message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/inbox")
async def get_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get messages for current user
    """
    try:
        # Get employee_id
        employee_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(employee_query, {"user_id": current_user.id})
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )
        
        employee_id = employee[0]
        
        # Get messages via inbox_notifications
        messages_query = text("""
            SELECT 
                n.id as notification_id,
                m.id as message_id,
                m.sender_employee_id,
                e.first_name || ' ' || e.last_name as sender_name,
                n.title,
                n.body,
                n.metadata,
                n.is_read,
                n.created_at,
                m.created_at as message_created_at
            FROM inbox_notifications n
            INNER JOIN messages m ON m.id = n.message_id
            INNER JOIN employees e ON e.id = m.sender_employee_id
            WHERE n.employee_id = :employee_id
            AND n.notification_type = 'message_received'
            ORDER BY n.created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = await db.execute(messages_query, {
            "employee_id": employee_id,
            "limit": limit,
            "skip": skip
        })
        
        messages = []
        for row in result.fetchall():
            messages.append({
                "notification_id": row[0],
                "message_id": row[1],
                "sender_employee_id": row[2],
                "sender_name": row[3],
                "title": row[4],
                "body": row[5],
                "metadata": row[6],
                "is_read": row[7],
                "received_at": row[8].isoformat() if row[8] else None,
                "sent_at": row[9].isoformat() if row[9] else None
            })
        
        return {
            "messages": messages,
            "total": len(messages),
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching messages: {e}")
        # Return empty messages if error occurs
        return {
            "messages": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "message": "Messages feature coming soon"
        }


@router.get("/{message_id}")
async def get_message_details(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get full message details
    """
    try:
        # Get employee_id
        employee_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(employee_query, {"user_id": current_user.id})
        employee = result.fetchone()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )
        
        employee_id = employee[0]
        
        # Get message details
        message_query = text("""
            SELECT 
                m.id,
                m.sender_employee_id,
                e.first_name || ' ' || e.last_name as sender_name,
                m.body,
                m.created_at,
                n.is_read,
                n.read_at
            FROM messages m
            INNER JOIN employees e ON e.id = m.sender_employee_id
            LEFT JOIN inbox_notifications n ON n.message_id = m.id 
                AND n.employee_id = :employee_id
            WHERE m.id = :message_id
            AND (m.sender_employee_id = :employee_id OR n.employee_id = :employee_id)
        """)
        
        result = await db.execute(message_query, {
            "message_id": message_id,
            "employee_id": employee_id
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or access denied"
            )
        
        # Parse subject and body
        body_text = row[3]
        subject = ""
        body = body_text
        
        if body_text.startswith("Subject: "):
            parts = body_text.split("\n\n", 1)
            if len(parts) == 2:
                subject = parts[0].replace("Subject: ", "")
                body = parts[1]
        
        return {
            "message_id": row[0],
            "sender_employee_id": row[1],
            "sender_name": row[2],
            "subject": subject,
            "body": body,
            "sent_at": row[4].isoformat() if row[4] else None,
            "is_read": row[5],
            "read_at": row[6].isoformat() if row[6] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching message details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch message details"
        )

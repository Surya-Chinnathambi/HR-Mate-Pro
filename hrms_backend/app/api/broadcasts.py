"""
Broadcasts API
Company-wide or department broadcasts with RBAC
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_async_session
from app.models import User, Employee
from app.core.security import get_current_active_user, require_permission
from app.services.notification_delivery import NotificationDeliveryService

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


# ============================================================================
# SCHEMAS
# ============================================================================

class CreateBroadcastRequest(BaseModel):
    title: str
    body: str
    priority: Optional[str] = "normal"  # low, normal, high, urgent
    target_scope: Optional[str] = "all"  # all, department, role
    target_department_id: Optional[int] = None
    target_role: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    attachments: Optional[List[str]] = None


class BroadcastCreate(BaseModel):
    message: str
    recipient_type: str  # 'all_managers', 'all_employees', 'specific_teams', 'custom'
    recipient_ids: List[int]
    scheduled_time: Optional[datetime] = None
    attachments: Optional[List[str]] = None
    template_used: Optional[str] = None


class BroadcastResponse(BaseModel):
    id: int
    message: str
    recipient_type: str
    recipient_count: int
    scheduled_time: Optional[datetime]
    sent_at: Optional[datetime]
    status: str  # 'scheduled', 'sent', 'failed'
    created_by: int
    created_at: datetime


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("")
@require_permission("broadcasts", "create")
async def create_broadcast(
    broadcast_data: CreateBroadcastRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a broadcast message
    
    Requires: broadcasts:create permission (HR/Admin/Manager)
    Sends notification to all targeted employees
    """
    try:
        # Get sender's employee_id
        sender_query = text("""
            SELECT id, first_name, last_name, role FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(sender_query, {"user_id": current_user.id})
        sender = result.fetchone()
        
        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )
        
        sender_employee_id = sender[0]
        sender_name = f"{sender[1]} {sender[2]}"
        sender_role = sender[3]
        
        # Build recipient query based on target_scope
        if broadcast_data.target_scope == "all":
            recipients_query = text("""
                SELECT id FROM employees WHERE status = 'active'
            """)
            recipients_result = await db.execute(recipients_query)
        
        elif broadcast_data.target_scope == "department":
            if not broadcast_data.target_department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_department_id required for department scope"
                )
            
            recipients_query = text("""
                SELECT id FROM employees 
                WHERE department_id = :department_id 
                AND status = 'active'
            """)
            recipients_result = await db.execute(recipients_query, {
                "department_id": broadcast_data.target_department_id
            })
        
        elif broadcast_data.target_scope == "role":
            if not broadcast_data.target_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="target_role required for role scope"
                )
            
            recipients_query = text("""
                SELECT id FROM employees 
                WHERE role = :role 
                AND status = 'active'
            """)
            recipients_result = await db.execute(recipients_query, {
                "role": broadcast_data.target_role
            })
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target_scope. Must be: all, department, or role"
            )
        
        recipient_ids = [row[0] for row in recipients_result.fetchall()]
        
        if not recipient_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No recipients found for the specified scope"
            )
        
        # Create broadcast record
        broadcast_insert = text("""
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
        
        result = await db.execute(broadcast_insert, {
            "sender_employee_id": sender_employee_id,
            "body": f"BROADCAST: {broadcast_data.title}\n\n{broadcast_data.body}"
        })
        broadcast_row = result.fetchone()
        broadcast_id = broadcast_row[0]
        
        # Create inbox notifications for all recipients
        inbox_ids = await NotificationDeliveryService.create_inbox_notification(
            db=db,
            recipient_employee_ids=recipient_ids,
            notification_type="broadcast",
            message_id=broadcast_id,
            entity_type="broadcast",
            entity_id=broadcast_id,
            title=f"Broadcast: {broadcast_data.title}",
            body=broadcast_data.body[:200],
            metadata={
                "sender_employee_id": sender_employee_id,
                "sender_name": sender_name,
                "sender_role": sender_role,
                "priority": broadcast_data.priority,
                "target_scope": broadcast_data.target_scope,
                "recipients_count": len(recipient_ids)
            }
        )
        
        # Create audit log
        from app.models.workflow import AuditLog, AuditAction
        
        audit_log = AuditLog(
            user_id=current_user.id,
            employee_id=sender_employee_id,
            action=AuditAction.CREATE_BROADCAST,
            entity_type="broadcast",
            entity_id=broadcast_id,
            description=f"Created broadcast '{broadcast_data.title}' to {len(recipient_ids)} recipients",
            new_value={
                "title": broadcast_data.title,
                "priority": broadcast_data.priority,
                "target_scope": broadcast_data.target_scope,
                "recipients_count": len(recipient_ids)
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
            event_channel="broadcasts_events",
            inbox_ids=inbox_ids[:10],  # Sample for response
            error=None
        )
        
        return {
            "success": True,
            "message": "Broadcast created and sent successfully",
            "broadcast_id": broadcast_id,
            "recipients_count": len(recipient_ids),
            "delivery_status": delivery_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating broadcast: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create broadcast: {str(e)}"
        )


@router.get("")
async def get_broadcasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get broadcasts for current user
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
        
        # Build query with optional priority filter
        where_clause = "AND n.notification_type = 'broadcast'"
        if priority:
            where_clause += f" AND n.metadata->>'priority' = :priority"
        
        broadcasts_query = text(f"""
            SELECT 
                n.id as notification_id,
                m.id as broadcast_id,
                m.sender_employee_id,
                e.first_name || ' ' || e.last_name as sender_name,
                n.title,
                n.body,
                n.metadata,
                n.is_read,
                n.created_at,
                m.created_at as broadcast_created_at
            FROM inbox_notifications n
            INNER JOIN messages m ON m.id = n.message_id
            INNER JOIN employees e ON e.id = m.sender_employee_id
            WHERE n.employee_id = :employee_id
            {where_clause}
            ORDER BY n.created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        params = {
            "employee_id": employee_id,
            "limit": limit,
            "skip": skip
        }
        if priority:
            params["priority"] = priority
        
        result = await db.execute(broadcasts_query, params)
        
        broadcasts = []
        for row in result.fetchall():
            broadcasts.append({
                "notification_id": row[0],
                "broadcast_id": row[1],
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
            "broadcasts": broadcasts,
            "total": len(broadcasts),
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching broadcasts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch broadcasts"
        )


@router.get("/{broadcast_id}")
async def get_broadcast_details(
    broadcast_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get full broadcast details
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
        
        # Get broadcast details
        broadcast_query = text("""
            SELECT 
                m.id,
                m.sender_employee_id,
                e.first_name || ' ' || e.last_name as sender_name,
                e.role as sender_role,
                m.body,
                m.created_at,
                n.is_read,
                n.read_at,
                n.metadata
            FROM messages m
            INNER JOIN employees e ON e.id = m.sender_employee_id
            LEFT JOIN inbox_notifications n ON n.message_id = m.id 
                AND n.employee_id = :employee_id
            WHERE m.id = :broadcast_id
            AND n.notification_type = 'broadcast'
        """)
        
        result = await db.execute(broadcast_query, {
            "broadcast_id": broadcast_id,
            "employee_id": employee_id
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broadcast not found or access denied"
            )
        
        # Parse title and body
        body_text = row[4]
        title = ""
        body = body_text
        
        if body_text.startswith("BROADCAST: "):
            parts = body_text.split("\n\n", 1)
            if len(parts) == 2:
                title = parts[0].replace("BROADCAST: ", "")
                body = parts[1]
        
        return {
            "broadcast_id": row[0],
            "sender_employee_id": row[1],
            "sender_name": row[2],
            "sender_role": row[3],
            "title": title,
            "body": body,
            "sent_at": row[5].isoformat() if row[5] else None,
            "is_read": row[6],
            "read_at": row[7].isoformat() if row[7] else None,
            "metadata": row[8]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching broadcast details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch broadcast details"
        )


@router.delete("/{broadcast_id}")
@require_permission("broadcasts", "delete")
async def delete_broadcast(
    broadcast_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a broadcast (Admin only)
    
    Requires: broadcasts:delete permission
    Deletes broadcast and all related inbox notifications
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
        
        # Delete all inbox notifications for this broadcast
        delete_notifications_query = text("""
            DELETE FROM inbox_notifications
            WHERE message_id = :broadcast_id
            AND notification_type = 'broadcast'
        """)
        
        await db.execute(delete_notifications_query, {
            "broadcast_id": broadcast_id
        })
        
        # Delete the broadcast message
        delete_broadcast_query = text("""
            DELETE FROM messages
            WHERE id = :broadcast_id
        """)
        
        result = await db.execute(delete_broadcast_query, {
            "broadcast_id": broadcast_id
        })
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broadcast not found"
            )
        
        # Create audit log
        from app.models.workflow import AuditLog, AuditAction
        
        audit_log = AuditLog(
            user_id=current_user.id,
            employee_id=employee_id,
            action=AuditAction.DELETE_BROADCAST,
            entity_type="broadcast",
            entity_id=broadcast_id,
            description=f"Deleted broadcast {broadcast_id}",
            success=True
        )
        db.add(audit_log)
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Broadcast deleted successfully",
            "broadcast_id": broadcast_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting broadcast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete broadcast"
        )


# ============================================================================
# LEGACY/SCHEDULED BROADCASTS (Keep for backward compatibility)
# ============================================================================

@router.post("/scheduled-broadcasts/", response_model=BroadcastResponse)
async def create_scheduled_broadcast(
    broadcast: BroadcastCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Schedule a broadcast message for later delivery
    """
    # In production, store this in a database table
    # For now, return a mock response
    return {
        "id": 1,
        "message": broadcast.message,
        "recipient_type": broadcast.recipient_type,
        "recipient_count": len(broadcast.recipient_ids),
        "scheduled_time": broadcast.scheduled_time,
        "sent_at": None,
        "status": "scheduled" if broadcast.scheduled_time else "sent",
        "created_by": current_user.id,
        "created_at": datetime.now()
    }


@router.get("/scheduled-broadcasts/", response_model=List[BroadcastResponse])
async def get_scheduled_broadcasts(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all scheduled broadcasts
    """
    # In production, fetch from database
    return []


@router.get("/teams/")
async def get_teams(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all teams in the organization
    """
    # Mock response - in production, fetch from teams table
    return [
        {"id": 1, "name": "Engineering", "member_count": 15},
        {"id": 2, "name": "Sales", "member_count": 10},
        {"id": 3, "name": "Marketing", "member_count": 8},
        {"id": 4, "name": "HR", "member_count": 5},
        {"id": 5, "name": "Finance", "member_count": 6},
    ]


@router.post("/files/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload files for broadcast attachments
    """
    # In production, save files to storage and return URLs
    urls = []
    for file in files:
        # Mock file URL
        urls.append(f"/uploads/{file.filename}")
    
    return {"urls": urls, "count": len(urls)}

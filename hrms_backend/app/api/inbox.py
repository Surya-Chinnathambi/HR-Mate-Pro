"""
Inbox Notifications API
Provides endpoints for viewing and managing inbox notifications
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, text
from typing import Optional, List
from datetime import datetime

from app.database import get_async_session
from app.core.security import get_current_active_user
from app.core.rbac import require_permission
from app.models.user import User

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("/notifications")
async def get_inbox_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    is_read: Optional[bool] = Query(None),
    notification_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get user's inbox notifications with pagination and filters
    
    Query Parameters:
        skip: Number of records to skip (default 0)
        limit: Max records to return (default 50, max 100)
        is_read: Filter by read status (true/false/null for all)
        notification_type: Filter by type (task_assigned, leave_approved, etc.)
    """
    try:
        # Check if inbox_notifications table exists
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'inbox_notifications'
            )
        """)
        table_exists = await db.execute(check_table)
        exists = table_exists.scalar()
        
        if not exists:
            # Return empty list if table doesn't exist yet
            return {
                "notifications": [],
                "total": 0,
                "skip": skip,
                "limit": limit
            }
        
        # Get employee_id for current user
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
        
        # Build query
        query = text("""
            SELECT 
                n.id,
                n.employee_id,
                n.notification_type,
                n.message_id,
                n.entity_type,
                n.entity_id,
                n.title,
                n.body,
                n.metadata,
                n.is_read,
                n.read_at,
                n.created_at,
                n.delivery_channel
            FROM inbox_notifications n
            WHERE n.employee_id = :employee_id
            AND (:is_read IS NULL OR n.is_read = :is_read)
            AND (:notification_type IS NULL OR n.notification_type = :notification_type)
            ORDER BY n.created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = await db.execute(query, {
            "employee_id": employee_id,
            "is_read": is_read,
            "notification_type": notification_type,
            "limit": limit,
            "skip": skip
        })
        
        notifications = []
        for row in result.fetchall():
            notifications.append({
                "id": row[0],
                "employee_id": row[1],
                "notification_type": row[2],
                "message_id": row[3],
                "entity_type": row[4],
                "entity_id": row[5],
                "title": row[6],
                "body": row[7],
                "metadata": row[8],
                "is_read": row[9],
                "read_at": row[10].isoformat() if row[10] else None,
                "created_at": row[11].isoformat() if row[11] else None,
                "delivery_channel": row[12]
            })
        
        # Get unread count
        count_query = text("""
            SELECT COUNT(*) FROM inbox_notifications
            WHERE employee_id = :employee_id AND is_read = false
        """)
        count_result = await db.execute(count_query, {"employee_id": employee_id})
        unread_count = count_result.scalar()
        
        return {
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": unread_count,
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching inbox notifications: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notifications"
        )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Mark a notification as read
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
        
        # Update notification
        update_query = text("""
            UPDATE inbox_notifications
            SET is_read = true, read_at = NOW()
            WHERE id = :notification_id AND employee_id = :employee_id
            RETURNING id
        """)
        
        result = await db.execute(update_query, {
            "notification_id": notification_id,
            "employee_id": employee_id
        })
        await db.commit()
        
        updated_row = result.fetchone()
        
        if not updated_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied"
            )
        
        return {
            "success": True,
            "message": "Notification marked as read",
            "notification_id": notification_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error marking notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Mark all user's notifications as read
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
        
        # Update all unread notifications
        update_query = text("""
            UPDATE inbox_notifications
            SET is_read = true, read_at = NOW()
            WHERE employee_id = :employee_id AND is_read = false
        """)
        
        result = await db.execute(update_query, {"employee_id": employee_id})
        await db.commit()
        
        return {
            "success": True,
            "message": f"Marked {result.rowcount} notifications as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error marking all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications as read"
        )


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete a notification
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
        
        # Delete notification
        delete_query = text("""
            DELETE FROM inbox_notifications
            WHERE id = :notification_id AND employee_id = :employee_id
            RETURNING id
        """)
        
        result = await db.execute(delete_query, {
            "notification_id": notification_id,
            "employee_id": employee_id
        })
        await db.commit()
        
        deleted_row = result.fetchone()
        
        if not deleted_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied"
            )
        
        return {
            "success": True,
            "message": "Notification deleted",
            "notification_id": notification_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification"
        )


@router.get("/stats")
async def get_inbox_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get inbox statistics (unread count, by type, etc.)
    """
    try:
        # Check if inbox_notifications table exists
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'inbox_notifications'
            )
        """)
        table_exists = await db.execute(check_table)
        exists = table_exists.scalar()
        
        if not exists:
            # Return empty stats if table doesn't exist yet
            return {
                "total": 0,
                "unread": 0,
                "read": 0,
                "by_type": {
                    "tasks": 0,
                    "leaves": 0,
                    "messages": 0,
                    "attendance": 0
                }
            }
        
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
        
        # Get stats
        stats_query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_read = false) as unread,
                COUNT(*) FILTER (WHERE is_read = true) as read,
                COUNT(*) FILTER (WHERE notification_type = 'task_assigned') as tasks,
                COUNT(*) FILTER (WHERE notification_type LIKE 'leave_%') as leaves,
                COUNT(*) FILTER (WHERE notification_type LIKE 'message_%') as messages,
                COUNT(*) FILTER (WHERE notification_type LIKE 'attendance_%') as attendance
            FROM inbox_notifications
            WHERE employee_id = :employee_id
        """)
        
        result = await db.execute(stats_query, {"employee_id": employee_id})
        row = result.fetchone()
        
        return {
            "total": row[0],
            "unread": row[1],
            "read": row[2],
            "by_type": {
                "tasks": row[3],
                "leaves": row[4],
                "messages": row[5],
                "attendance": row[6]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching inbox stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inbox stats"
        )

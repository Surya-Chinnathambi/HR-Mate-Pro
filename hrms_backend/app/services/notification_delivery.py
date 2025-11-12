"""
Notification Delivery Service

Provides standardized methods for creating inbox notifications and emitting events.
Used by automation services to implement the 4-step pattern:
1. RBAC validation (done by caller)
2. DB transaction (primary entity + inbox notification + audit log)
3. Event emission (pg_notify for downstream workers)
4. Return detailed delivery status
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
import json


class NotificationDeliveryService:
    """
    Centralized service for creating inbox notifications and emitting events.
    
    All automation services should use this to ensure consistent delivery patterns.
    """
    
    @staticmethod
    async def create_inbox_notification(
        db: AsyncSession,
        recipient_employee_ids: List[int],
        notification_type: str,
        message_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create inbox notification for one or more recipients.
        
        Args:
            db: Database session
            recipient_employee_ids: List of employee IDs to notify
            notification_type: Type (message, task, leave, approval, broadcast)
            message_id: Optional message UUID if linked to message
            entity_type: Type of entity (work_assignment, leave_application, etc.)
            entity_id: ID of the entity
            title: Notification title
            body: Notification body/preview
            metadata: Additional JSON metadata
        
        Returns:
            Dict with inbox_ids created and delivery status
        """
        inbox_ids = []
        
        try:
            for recipient_id in recipient_employee_ids:
                inbox_id = str(uuid.uuid4())
                
                # If no message_id provided, we need to create a message first
                if not message_id:
                    msg_id = str(uuid.uuid4())
                    # Insert into messages table (will trigger emit_message_event)
                    await db.execute(
                        text("""
                            INSERT INTO messages (message_id, subject, content, message_type, priority, created_at)
                            VALUES (:message_id, :subject, :content, :message_type, :priority, now())
                        """),
                        {
                            "message_id": msg_id,
                            "subject": title or "Notification",
                            "content": body or "",
                            "message_type": notification_type,
                            "priority": "normal"
                        }
                    )
                    message_id = msg_id
                
                # Insert into inbox_notifications (will trigger emit_inbox_event)
                await db.execute(
                    text("""
                        INSERT INTO inbox_notifications (
                            inbox_id, user_id, message_id, notification_type, 
                            is_read, delivered_at, metadata
                        )
                        VALUES (:inbox_id, :user_id, :message_id, :notification_type, 
                                false, now(), :metadata)
                    """),
                    {
                        "inbox_id": inbox_id,
                        "user_id": recipient_id,
                        "message_id": message_id,
                        "notification_type": notification_type,
                        "metadata": json.dumps(metadata or {})
                    }
                )
                
                inbox_ids.append(inbox_id)
            
            return {
                "success": True,
                "inbox_ids": inbox_ids,
                "recipients_count": len(recipient_employee_ids),
                "message_id": message_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "inbox_ids": inbox_ids  # Partial success possible
            }
    
    @staticmethod
    async def emit_custom_event(
        db: AsyncSession,
        channel: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Emit a custom PostgreSQL NOTIFY event.
        
        This is useful for events that don't have automatic triggers.
        
        Args:
            db: Database session
            channel: PostgreSQL NOTIFY channel name
            event_type: Event type identifier
            payload: Event payload (will be JSON serialized)
        
        Returns:
            Dict with emission status
        """
        try:
            payload_with_type = {
                "event_type": event_type,
                **payload
            }
            
            await db.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {
                    "channel": channel,
                    "payload": json.dumps(payload_with_type)
                }
            )
            
            return {
                "success": True,
                "channel": channel,
                "event_type": event_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "channel": channel
            }
    
    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        user_id: Optional[int],
        employee_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[int],
        description: str,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create audit log entry.
        
        Args:
            db: Database session
            user_id: User ID (from users table)
            employee_id: Employee ID
            action: Action type (create, update, delete, approve, etc.)
            entity_type: Type of entity affected
            entity_id: ID of entity
            description: Human-readable description
            old_value: Previous state (JSON)
            new_value: New state (JSON)
            success: Whether action succeeded
            error_message: Error message if failed
        
        Returns:
            Dict with audit log ID and status
        """
        try:
            audit_id = str(uuid.uuid4())
            
            await db.execute(
                text("""
                    INSERT INTO audit_logs (
                        audit_id, actor_id, action_type, resource_type, resource_id,
                        target_user_id, old_value, new_value, success, error_message, created_at
                    )
                    VALUES (:audit_id, :actor_id, :action_type, :resource_type, :resource_id,
                            :target_user_id, :old_value, :new_value, :success, :error_message, now())
                """),
                {
                    "audit_id": audit_id,
                    "actor_id": employee_id,
                    "action_type": action,
                    "resource_type": entity_type,
                    "resource_id": str(entity_id) if entity_id else None,
                    "target_user_id": employee_id,
                    "old_value": json.dumps(old_value) if old_value else None,
                    "new_value": json.dumps(new_value) if new_value else None,
                    "success": success,
                    "error_message": error_message
                }
            )
            
            return {
                "success": True,
                "audit_id": audit_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def build_delivery_status(
        entity_created: bool = False,
        inbox_created: bool = False,
        event_emitted: bool = False,
        audit_logged: bool = False,
        event_channel: Optional[str] = None,
        inbox_ids: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build standardized delivery status response.
        
        Returns:
            Dict with detailed delivery status
        """
        status = {
            "entity_created": entity_created,
            "inbox_notification_created": inbox_created,
            "event_emitted": event_emitted,
            "audit_logged": audit_logged
        }
        
        if event_channel:
            status["event_channel"] = event_channel
        
        if inbox_ids:
            status["inbox_ids"] = inbox_ids
            status["recipients_notified"] = len(inbox_ids)
        
        if error:
            status["error"] = error
        
        return status

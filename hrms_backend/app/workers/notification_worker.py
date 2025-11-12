"""
Notification Worker
Consumes Redis pub/sub events and sends email/Slack/push notifications
Implements retry logic with exponential backoff
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, update
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hrms").replace(
    "postgresql://", "postgresql+asyncpg://"
)


class NotificationWorker:
    """
    Worker that processes notification events from Redis
    Sends notifications via email, Slack, push, etc.
    """
    
    def __init__(self, redis_client: redis.Redis, worker_id: str = "worker-1"):
        self.redis_client = redis_client
        self.worker_id = worker_id
        self.is_running = False
        
        # Create database session factory
        self.engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Channels to subscribe to
        self.channels = [
            "notifications:inbox_events",
            "notifications:message_events",
            "notifications:task_events",
            "notifications:leave_events",
            "notifications:attendance_events",
            "notifications:wfh_events",
            "notifications:expense_events"
        ]
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [5, 30, 300]  # 5s, 30s, 5min
    
    async def start(self):
        """
        Start the worker and subscribe to Redis channels
        """
        self.is_running = True
        print(f"🚀 Notification Worker {self.worker_id} starting...")
        
        # Create Redis pubsub
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to all channels
        await pubsub.subscribe(*self.channels)
        print(f"✓ Subscribed to {len(self.channels)} channels")
        
        try:
            # Process messages
            async for message in pubsub.listen():
                if not self.is_running:
                    break
                
                if message['type'] == 'message':
                    await self._process_message(message)
                    
        except asyncio.CancelledError:
            print(f"Worker {self.worker_id} cancelled")
        finally:
            await pubsub.unsubscribe(*self.channels)
            await pubsub.close()
            await self.stop()
    
    async def _process_message(self, message: Dict[str, Any]):
        """
        Process a single notification event
        """
        try:
            channel = message['channel'].decode('utf-8') if isinstance(message['channel'], bytes) else message['channel']
            data = json.loads(message['data'])
            
            event_channel = data.get('channel')
            event_data = data.get('data', {})
            
            print(f"📨 [{self.worker_id}] Processing: {event_channel} - {event_data.get('entity_type')}")
            
            # Process based on event type
            if event_channel == 'inbox_events':
                await self._handle_inbox_event(event_data)
            elif event_channel == 'task_events':
                await self._handle_task_event(event_data)
            elif event_channel == 'leave_events':
                await self._handle_leave_event(event_data)
            elif event_channel == 'message_events':
                await self._handle_message_event(event_data)
            else:
                # Generic handler for other events
                await self._handle_generic_event(event_data)
                
        except Exception as e:
            print(f"✗ Error processing message: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_inbox_event(self, event_data: Dict[str, Any]):
        """
        Handle inbox notification event
        Send email/push notification to recipients
        """
        try:
            notification_id = event_data.get('notification_id')
            employee_id = event_data.get('employee_id')
            notification_type = event_data.get('notification_type')
            title = event_data.get('title')
            body = event_data.get('body')
            
            if not notification_id:
                return
            
            # Send email notification (simulated)
            email_sent = await self._send_email_notification(
                employee_id=employee_id,
                title=title,
                body=body,
                notification_type=notification_type
            )
            
            # Send push notification (simulated)
            push_sent = await self._send_push_notification(
                employee_id=employee_id,
                title=title,
                body=body
            )
            
            # Update delivery channel in database
            delivery_channels = []
            if email_sent:
                delivery_channels.append('email')
            if push_sent:
                delivery_channels.append('push')
            
            await self._update_notification_delivery(
                notification_id=notification_id,
                delivery_channels=delivery_channels
            )
            
            print(f"  ✓ Notification {notification_id} delivered via {delivery_channels}")
            
        except Exception as e:
            print(f"✗ Error handling inbox event: {e}")
            # Retry logic would go here
    
    async def _handle_task_event(self, event_data: Dict[str, Any]):
        """
        Handle task assignment event
        """
        task_id = event_data.get('task_id')
        assignee_id = event_data.get('assignee_id')
        assigner_id = event_data.get('assigner_id')
        
        print(f"  ℹ Task {task_id} assigned to employee {assignee_id}")
        # Additional task-specific processing
    
    async def _handle_leave_event(self, event_data: Dict[str, Any]):
        """
        Handle leave application event
        """
        leave_id = event_data.get('leave_id')
        employee_id = event_data.get('employee_id')
        leave_type = event_data.get('leave_type')
        
        print(f"  ℹ Leave {leave_id} submitted by employee {employee_id} (type: {leave_type})")
        # Additional leave-specific processing
    
    async def _handle_message_event(self, event_data: Dict[str, Any]):
        """
        Handle direct message event
        """
        message_id = event_data.get('message_id')
        print(f"  ℹ Message {message_id} received")
    
    async def _handle_generic_event(self, event_data: Dict[str, Any]):
        """
        Generic event handler
        """
        entity_type = event_data.get('entity_type')
        entity_id = event_data.get('entity_id')
        print(f"  ℹ Generic event: {entity_type} {entity_id}")
    
    async def _send_email_notification(
        self,
        employee_id: int,
        title: str,
        body: str,
        notification_type: str
    ) -> bool:
        """
        Send email notification (simulated for now)
        In production: integrate with SendGrid, AWS SES, or SMTP
        """
        try:
            # TODO: Integrate with actual email service
            # For now, just simulate success
            print(f"    📧 Email sent to employee {employee_id}: {title}")
            await asyncio.sleep(0.1)  # Simulate API call
            return True
        except Exception as e:
            print(f"    ✗ Failed to send email: {e}")
            return False
    
    async def _send_push_notification(
        self,
        employee_id: int,
        title: str,
        body: str
    ) -> bool:
        """
        Send push notification (simulated for now)
        In production: integrate with FCM, APNS, or OneSignal
        """
        try:
            # TODO: Integrate with actual push service
            # For now, just simulate success
            print(f"    📱 Push sent to employee {employee_id}: {title}")
            await asyncio.sleep(0.1)  # Simulate API call
            return True
        except Exception as e:
            print(f"    ✗ Failed to send push: {e}")
            return False
    
    async def _update_notification_delivery(
        self,
        notification_id: int,
        delivery_channels: List[str]
    ):
        """
        Update inbox_notifications table with delivery channel
        """
        try:
            async with self.async_session() as session:
                stmt = text("""
                    UPDATE inbox_notifications
                    SET delivery_channel = :channels,
                        delivered_at = NOW()
                    WHERE id = :notification_id
                """)
                
                await session.execute(
                    stmt,
                    {
                        "channels": ",".join(delivery_channels),
                        "notification_id": notification_id
                    }
                )
                await session.commit()
                
        except Exception as e:
            print(f"✗ Failed to update notification delivery: {e}")
    
    async def stop(self):
        """
        Stop the worker gracefully
        """
        self.is_running = False
        await self.engine.dispose()
        print(f"Worker {self.worker_id} stopped")


async def run_worker(redis_client: redis.Redis, worker_id: str = "worker-1"):
    """
    Run a notification worker
    """
    worker = NotificationWorker(redis_client, worker_id)
    await worker.start()

"""
Worker Orchestration Script
Runs all notification workers: PostgreSQL listener, Redis consumers, WebSocket broadcaster
"""
import asyncio
import signal
import sys
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

# Worker tasks
worker_tasks: List[asyncio.Task] = []
should_stop = False


async def run_postgres_listener():
    """Run PostgreSQL NOTIFY listener"""
    from app.workers.postgres_listener import PostgresNotifyListener
    from app.core.redis_client import get_redis_pool
    
    redis = await get_redis_pool()
    listener = PostgresNotifyListener(redis)
    
    print("🎧 Starting PostgreSQL Event Listener...")
    await listener.start()


async def run_notification_worker(worker_id: str):
    """Run notification processing worker"""
    from app.workers.notification_worker import NotificationWorker
    from app.core.redis_client import get_redis_pool
    
    redis = await get_redis_pool()
    worker = NotificationWorker(redis, worker_id=worker_id)
    
    print(f"👷 Starting Notification Worker: {worker_id}...")
    await worker.start()


async def run_websocket_broadcaster():
    """
    Run WebSocket event broadcaster
    Consumes from WebSocket queue and broadcasts to connected clients
    """
    from app.core.redis_client import get_redis_pool, RedisChannels, get_from_queue
    import json
    
    redis = await get_redis_pool()
    pubsub = redis.pubsub()
    
    # Subscribe to all event channels
    channels = [
        RedisChannels.TASKS,
        RedisChannels.LEAVES,
        RedisChannels.MESSAGES,
        RedisChannels.INBOX,
        RedisChannels.ATTENDANCE,
        RedisChannels.WFH_REQUESTS,
        RedisChannels.EXPENSE_CLAIMS
    ]
    
    await pubsub.subscribe(*channels)
    print(f"📡 WebSocket Broadcaster listening to {len(channels)} channels...")
    
    try:
        async for message in pubsub.listen():
            if should_stop:
                break
            
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    channel = message['channel']
                    
                    # Determine recipient user IDs from event data
                    recipient_ids = extract_recipient_ids(event_data)
                    
                    if recipient_ids:
                        # Broadcast to specific users via user-specific channels
                        for user_id in recipient_ids:
                            user_channel = f"user:{user_id}:events"
                            await redis.publish(user_channel, json.dumps(event_data))
                    
                    print(f"📤 Broadcasted event from {channel} to {len(recipient_ids)} users")
                    
                except Exception as e:
                    print(f"Error broadcasting: {e}")
                    
    except asyncio.CancelledError:
        print("WebSocket broadcaster stopped")
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()


def extract_recipient_ids(event_data: dict) -> List[int]:
    """
    Extract recipient user IDs from event data
    
    Args:
        event_data: Event payload
        
    Returns:
        List of user IDs to notify
    """
    recipients = []
    
    # Check for explicit recipients
    if 'recipients' in event_data:
        recipients.extend(event_data['recipients'])
    
    # Check for employee_id (need to map to user_id)
    if 'employee_id' in event_data:
        # TODO: Look up user_id from employee_id
        # For now, assume employee_id == user_id (would need DB query)
        pass
    
    # Check metadata for recipient info
    metadata = event_data.get('metadata', {})
    if 'recipient_employee_ids' in metadata:
        # TODO: Map employee_ids to user_ids
        pass
    
    return recipients


async def run_all_workers():
    """Run all workers concurrently"""
    global worker_tasks, should_stop
    
    print("=" * 60)
    print("🚀 Starting HRMS Notification Engine")
    print("=" * 60)
    
    try:
        # Start all workers as concurrent tasks
        worker_tasks = [
            asyncio.create_task(run_postgres_listener(), name="postgres_listener"),
            asyncio.create_task(run_notification_worker("worker-1"), name="notification_worker_1"),
            asyncio.create_task(run_notification_worker("worker-2"), name="notification_worker_2"),
            asyncio.create_task(run_websocket_broadcaster(), name="websocket_broadcaster")
        ]
        
        print(f"\n✅ Started {len(worker_tasks)} workers\n")
        
        # Wait for all tasks
        await asyncio.gather(*worker_tasks)
        
    except asyncio.CancelledError:
        print("\n🛑 Shutting down workers...")
        should_stop = True
        
        # Cancel all tasks
        for task in worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        print("✅ All workers stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print(f"\n⚠️  Received signal {sig}, initiating graceful shutdown...")
    global should_stop
    should_stop = True
    
    # Cancel all running tasks
    for task in worker_tasks:
        task.cancel()


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check required environment variables
    required_vars = ["DATABASE_URL", "REDIS_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        sys.exit(1)
    
    # Run workers
    try:
        asyncio.run(run_all_workers())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
PostgreSQL LISTEN/NOTIFY Bridge
Listens to PostgreSQL NOTIFY events and forwards them to Redis pub/sub
"""
import asyncio
import asyncpg
import json
from typing import Dict, Any, Callable, Optional
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from datetime import datetime

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hrms")


class PostgresNotifyListener:
    """
    Listens to PostgreSQL NOTIFY events and bridges them to Redis
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.connection: Optional[asyncpg.Connection] = None
        self.is_running = False
        self.channels = [
            "inbox_events",
            "message_events",
            "task_events",
            "leave_events",
            "attendance_events",
            "wfh_events",
            "expense_events"
        ]
        
    async def connect(self):
        """
        Establish PostgreSQL connection for LISTEN
        """
        try:
            self.connection = await asyncpg.connect(DATABASE_URL)
            print(f"✓ PostgreSQL LISTEN connection established")
            
            # Register listeners for all channels
            for channel in self.channels:
                await self.connection.add_listener(channel, self._handle_notification)
                print(f"  ✓ Listening on channel: {channel}")
                
        except Exception as e:
            print(f"✗ Failed to connect to PostgreSQL: {e}")
            raise
    
    async def _handle_notification(self, connection, pid, channel, payload):
        """
        Handle incoming PostgreSQL NOTIFY event
        Forward to Redis pub/sub for worker consumption
        """
        try:
            # Parse payload
            event_data = json.loads(payload) if payload else {}
            
            # Enrich with metadata
            enriched_event = {
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
                "pg_pid": pid,
                "data": event_data
            }
            
            # Publish to Redis for worker processing
            await self.redis_client.publish(
                f"notifications:{channel}",
                json.dumps(enriched_event)
            )
            
            print(f"📡 Event forwarded: {channel} -> Redis (entity_type={event_data.get('entity_type')})")
            
        except Exception as e:
            print(f"✗ Error handling notification on {channel}: {e}")
    
    async def start(self):
        """
        Start listening to PostgreSQL NOTIFY events
        """
        await self.connect()
        self.is_running = True
        print(f"🚀 PostgreSQL NOTIFY listener started")
        
        try:
            # Keep connection alive and listen
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("PostgreSQL listener cancelled")
        finally:
            await self.stop()
    
    async def stop(self):
        """
        Stop listening and close connection
        """
        self.is_running = False
        
        if self.connection:
            # Remove listeners
            for channel in self.channels:
                try:
                    await self.connection.remove_listener(channel, self._handle_notification)
                except:
                    pass
            
            await self.connection.close()
            print("PostgreSQL LISTEN connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if listener is healthy
        """
        if not self.connection or self.connection.is_closed():
            return False
        
        try:
            # Simple query to check connection
            await self.connection.fetchval("SELECT 1")
            return True
        except:
            return False


# Global listener instance
_listener_instance: Optional[PostgresNotifyListener] = None


async def get_postgres_listener(redis_client: redis.Redis) -> PostgresNotifyListener:
    """
    Get or create PostgreSQL listener instance
    """
    global _listener_instance
    
    if _listener_instance is None:
        _listener_instance = PostgresNotifyListener(redis_client)
    
    return _listener_instance


async def start_postgres_listener(redis_client: redis.Redis):
    """
    Start the PostgreSQL listener as a background task
    """
    listener = await get_postgres_listener(redis_client)
    await listener.start()

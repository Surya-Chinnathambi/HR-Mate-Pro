"""
Redis Client Configuration
Provides Redis connection pooling for pub/sub, caching, and job queues
"""
import redis.asyncio as redis
import asyncio
from typing import Any
try:
    from upstash_redis import Redis as UpstashRedis
except Exception:
    UpstashRedis = None
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
UPSTASH_URL = os.getenv("UPSTASH_URL", None)
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN", None)

# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def get_redis_pool() -> redis.Redis:
    """
    Get or create Redis connection pool
    """
    global _redis_pool
    
    if _redis_pool is None:
        # If Upstash REST URL/token provided, use upstash_redis client wrapped for async
        if UPSTASH_URL and UpstashRedis is not None:
            client = UpstashRedis(url=UPSTASH_URL, token=UPSTASH_TOKEN)

            class UpstashWrapper:
                def __init__(self, client: Any):
                    self._client = client

                async def ping(self):
                    return await asyncio.to_thread(self._client.ping)

                async def publish(self, channel: str, message: str):
                    return await asyncio.to_thread(self._client.publish, channel, message)

                async def zadd(self, name: str, mapping: dict):
                    # upstash client zadd signature may accept mapping
                    return await asyncio.to_thread(self._client.zadd, name, mapping)

                async def zpopmin(self, name: str, count: int = 1):
                    return await asyncio.to_thread(self._client.zpopmin, name, count)

                async def bzpopmin(self, name: str, timeout: int = 0):
                    # Upstash does not support blocking pop; emulate with polling
                    end = asyncio.get_event_loop().time() + timeout
                    while True:
                        res = await self.zpopmin(name, 1)
                        if res:
                            # return in same shape as redis.bzpopmin: (name, member, score)
                            # upstash zpopmin returns list of tuples [(member, score)]
                            member, score = res[0]
                            return (name, member, score)
                        if timeout == 0 or asyncio.get_event_loop().time() >= end:
                            return None
                        await asyncio.sleep(0.5)

                async def close(self):
                    # upstash client has no close; noop
                    return None

                # allow attribute access
                def __getattr__(self, item):
                    attr = getattr(self._client, item)
                    if callable(attr):
                        return lambda *a, **kw: asyncio.to_thread(attr, *a, **kw)
                    return attr

            _redis_pool = UpstashWrapper(client)
        else:
            _redis_pool = redis.from_url(
                REDIS_URL,
                password=REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )

    return _redis_pool


async def close_redis_pool():
    """
    Close Redis connection pool
    """
    global _redis_pool
    
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def get_redis() -> redis.Redis:
    """
    Dependency for FastAPI endpoints to get Redis client
    """
    return await get_redis_pool()


async def ping_redis() -> bool:
    """
    Health check for Redis connection
    """
    try:
        pool = await get_redis_pool()
        return await pool.ping()
    except Exception as e:
        print(f"Redis health check failed: {e}")
        return False


class RedisChannels:
    """Redis pub/sub channel names (mirror PostgreSQL NOTIFY channels)"""
    TASKS = "tasks_events"
    LEAVES = "leave_requests_events"
    MESSAGES = "messages_events"
    INBOX = "inbox_events"
    ATTENDANCE = "attendance_events"
    WFH_REQUESTS = "wfh_request_events"
    EXPENSE_CLAIMS = "expense_claim_events"
    
    # Worker job queues
    EMAIL_QUEUE = "queue:email"
    SLACK_QUEUE = "queue:slack"
    PUSH_QUEUE = "queue:push"
    WEBSOCKET_QUEUE = "queue:websocket"
    
    # WebSocket connection tracking
    WS_CONNECTIONS = "ws:connections"
    WS_USER_PREFIX = "ws:user:"


class RedisKeys:
    """Redis key patterns"""
    
    @staticmethod
    def ws_user_connection(user_id: int) -> str:
        """Key for user's WebSocket connection data"""
        return f"{RedisChannels.WS_USER_PREFIX}{user_id}"
    
    @staticmethod
    def ws_connection_user(connection_id: str) -> str:
        """Key for connection's user mapping"""
        return f"ws:conn:{connection_id}"
    
    @staticmethod
    def notification_retry(notification_id: int) -> str:
        """Key for notification retry count"""
        return f"notification:retry:{notification_id}"
    
    @staticmethod
    def rate_limit(user_id: int, window: str) -> str:
        """Key for rate limiting"""
        return f"ratelimit:{window}:{user_id}"


async def publish_event(channel: str, event_data: dict):
    """
    Publish event to Redis channel
    
    Args:
        channel: Redis channel name
        event_data: Event payload (will be JSON serialized)
    """
    import json
    
    redis = await get_redis_pool()
    await redis.publish(channel, json.dumps(event_data))


async def add_to_queue(queue_name: str, job_data: dict, priority: int = 5):
    """
    Add job to Redis queue (priority queue using sorted set)
    
    Args:
        queue_name: Queue name
        job_data: Job payload
        priority: Job priority (1-10, higher = more urgent)
    """
    import json
    import time
    
    redis = await get_redis_pool()
    
    job = {
        "data": job_data,
        "priority": priority,
        "added_at": time.time(),
        "attempts": 0
    }
    
    # Use sorted set for priority queue (higher priority = higher score)
    await redis.zadd(queue_name, {json.dumps(job): -priority})  # Negative for ZPOPMIN


async def get_from_queue(queue_name: str, timeout: int = 5) -> Optional[dict]:
    """
    Get job from Redis queue (blocking pop with timeout)
    
    Args:
        queue_name: Queue name
        timeout: Timeout in seconds
        
    Returns:
        Job data or None if timeout
    """
    import json
    
    redis = await get_redis_pool()
    
    # Pop lowest score (highest priority) job
    result = await redis.bzpopmin(queue_name, timeout=timeout)
    
    if result:
        _, job_json, _ = result
        return json.loads(job_json)
    
    return None

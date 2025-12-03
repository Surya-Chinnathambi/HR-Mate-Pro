"""
Redis Client Configuration for Railway Redis
Simplified version using standard Redis
"""
import redis.asyncio as redis
from typing import Optional

# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def get_redis_pool() -> redis.Redis:
    """
    Get or create Redis connection pool from Railway environment
    Railway automatically provides REDIS_URL environment variable
    """
    global _redis_pool
    
    if _redis_pool is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        _redis_pool = redis.from_url(
            redis_url,
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

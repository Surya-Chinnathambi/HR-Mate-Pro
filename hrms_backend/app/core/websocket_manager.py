"""
WebSocket Manager for Real-time Notifications
Handles WebSocket connections, JWT authentication, and event broadcasting
"""
import asyncio
import json
from typing import Dict, Set, Optional
from datetime import datetime
import uuid
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_pool, RedisKeys, RedisChannels
from app.core.security import SECRET_KEY, ALGORITHM
from app.database import get_async_session


class ConnectionManager:
    """
    Manages WebSocket connections with Redis-backed storage
    Supports distributed deployments (multiple server instances)
    """
    
    def __init__(self):
        # Local in-memory storage (for this server instance)
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}  # user_id -> set of connection_ids
        
    async def connect(self, websocket: WebSocket, user_id: int, connection_id: str):
        """
        Accept new WebSocket connection and register it
        
        Args:
            websocket: WebSocket connection
            user_id: Authenticated user ID
            connection_id: Unique connection identifier
        """
        await websocket.accept()
        
        # Store locally
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store in Redis for distributed tracking
        redis = await get_redis_pool()
        
        connection_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'connected_at': datetime.utcnow().isoformat(),
            'server_instance': 'main'  # Could be hostname or instance ID
        }
        
        # Set user's connection data (with 24hr expiry)
        await redis.setex(
            RedisKeys.ws_user_connection(user_id),
            86400,  # 24 hours
            json.dumps(connection_data)
        )
        
        # Add to global connections hash
        await redis.hset(
            RedisChannels.WS_CONNECTIONS,
            str(user_id),
            connection_id
        )
        
        print(f"✓ WebSocket connected: user_id={user_id}, connection_id={connection_id}")
    
    async def disconnect(self, connection_id: str, user_id: int):
        """
        Remove WebSocket connection
        
        Args:
            connection_id: Connection identifier
            user_id: User ID
        """
        # Remove from local storage
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from Redis
        redis = await get_redis_pool()
        await redis.delete(RedisKeys.ws_user_connection(user_id))
        await redis.hdel(RedisChannels.WS_CONNECTIONS, str(user_id))
        
        print(f"✗ WebSocket disconnected: user_id={user_id}, connection_id={connection_id}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send message to specific user's connections
        
        Args:
            message: Message payload
            user_id: Target user ID
        """
        if user_id not in self.user_connections:
            print(f"User {user_id} not connected to this instance")
            return
        
        # Send to all user's connections
        for connection_id in list(self.user_connections[user_id]):
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Error sending to {connection_id}: {e}")
                    await self.disconnect(connection_id, user_id)
    
    async def send_to_multiple_users(self, message: dict, user_ids: list):
        """
        Send message to multiple users
        
        Args:
            message: Message payload
            user_ids: List of target user IDs
        """
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected users
        
        Args:
            message: Message payload
        """
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            # Find user_id for this connection
            for user_id, conn_ids in self.user_connections.items():
                if connection_id in conn_ids:
                    await self.disconnect(connection_id, user_id)
                    break
    
    def get_connected_users(self) -> list:
        """Get list of currently connected user IDs"""
        return list(self.user_connections.keys())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)


# Global connection manager instance
manager = ConnectionManager()


async def get_current_user_from_token(token: str, db: AsyncSession) -> Optional[dict]:
    """
    Authenticate WebSocket connection using JWT token
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        User data dict or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        
        if user_id is None:
            return None
        
        # Fetch user from database
        from sqlalchemy import select, text
        
        query = text("""
            SELECT u.id, u.email, u.username, u.is_active, e.id as employee_id
            FROM users u
            LEFT JOIN employees e ON e.user_id = u.id
            WHERE u.id = :user_id AND u.is_active = true
        """)
        
        result = await db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "email": row[1],
            "username": row[2],
            "is_active": row[3],
            "employee_id": row[4]
        }
        
    except JWTError:
        return None


async def websocket_auth(websocket: WebSocket, token: Optional[str] = None) -> Optional[dict]:
    """
    Authenticate WebSocket connection
    
    Token can be provided via:
    1. Query parameter: ?token=xxx
    2. During initial handshake message
    
    Args:
        websocket: WebSocket connection
        token: Optional JWT token
        
    Returns:
        User data or None
    """
    from app.database import async_session_maker
    
    async with async_session_maker() as db:
        if token:
            return await get_current_user_from_token(token, db)
        
        # Wait for auth message
        try:
            auth_message = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10.0
            )
            
            if auth_message.get('type') == 'auth':
                token = auth_message.get('token')
                if token:
                    return await get_current_user_from_token(token, db)
        except asyncio.TimeoutError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
    
    return None


async def handle_websocket_heartbeat(websocket: WebSocket, connection_id: str):
    """
    Handle heartbeat/ping-pong to keep connection alive
    
    Args:
        websocket: WebSocket connection
        connection_id: Connection identifier
    """
    try:
        while True:
            await asyncio.sleep(30)  # Send ping every 30 seconds
            try:
                await websocket.send_json({
                    'type': 'ping',
                    'timestamp': datetime.utcnow().isoformat()
                })
            except:
                break
    except asyncio.CancelledError:
        pass

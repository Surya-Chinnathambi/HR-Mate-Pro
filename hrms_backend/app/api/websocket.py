"""
WebSocket Real-time Updates using Socket.IO
Handles live notifications, approvals, and task updates
"""
from typing import Dict, Any
import socketio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Create Socket.IO async server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # TODO: Restrict in production
    logger=True,
    engineio_logger=True
)

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio)

# Store active connections: {user_id: [sid1, sid2, ...]}
user_connections: Dict[int, list] = {}

# Store user info: {sid: user_id}
sid_to_user: Dict[str, int] = {}


# ============================================================================
# SOCKET.IO EVENT HANDLERS
# ============================================================================

@sio.event
async def connect(sid: str, environ: dict, auth: dict = None):
    """
    Handle new WebSocket connection
    Auth should contain: {'token': 'Bearer <jwt_token>'}
    """
    logger.info(f"Client connecting: {sid}")
    
    try:
        # Extract token from auth
        if not auth or 'token' not in auth:
            logger.warning(f"Connection rejected - no token: {sid}")
            return False
        
        token = auth['token']
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Validate token (simplified - in production use proper JWT validation)
        # For now, we'll accept any token and store it
        # TODO: Implement proper JWT validation with get_current_user
        
        logger.info(f"Client connected successfully: {sid}")
        await sio.emit('connected', {'sid': sid, 'message': 'Connected successfully'}, room=sid)
        return True
        
    except Exception as e:
        logger.error(f"Connection error for {sid}: {str(e)}")
        return False


@sio.event
async def disconnect(sid: str):
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {sid}")
    
    # Clean up user connection tracking
    if sid in sid_to_user:
        user_id = sid_to_user[sid]
        if user_id in user_connections:
            user_connections[user_id].remove(sid)
            if not user_connections[user_id]:
                del user_connections[user_id]
        del sid_to_user[sid]


@sio.event
async def authenticate(sid: str, data: dict):
    """
    Authenticate user and join their personal room
    Data should contain: {'user_id': int, 'token': 'jwt_token'}
    """
    try:
        user_id = data.get('user_id')
        if not user_id:
            await sio.emit('error', {'message': 'user_id required'}, room=sid)
            return
        
        # Track user connection
        sid_to_user[sid] = user_id
        if user_id not in user_connections:
            user_connections[user_id] = []
        user_connections[user_id].append(sid)
        
        # Join user-specific room
        await sio.enter_room(sid, f"user_{user_id}")
        
        logger.info(f"User {user_id} authenticated with sid {sid}")
        await sio.emit('authenticated', {
            'user_id': user_id,
            'message': 'Authentication successful'
        }, room=sid)
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def subscribe_to_team(sid: str, data: dict):
    """
    Subscribe to team notifications (for managers)
    Data should contain: {'team_id': int} or {'department': str}
    """
    try:
        team_id = data.get('team_id')
        department = data.get('department')
        
        if team_id:
            await sio.enter_room(sid, f"team_{team_id}")
            logger.info(f"Client {sid} subscribed to team_{team_id}")
            await sio.emit('subscribed', {'room': f"team_{team_id}"}, room=sid)
        
        if department:
            await sio.enter_room(sid, f"dept_{department}")
            logger.info(f"Client {sid} subscribed to dept_{department}")
            await sio.emit('subscribed', {'room': f"dept_{department}"}, room=sid)
            
    except Exception as e:
        logger.error(f"Subscription error: {str(e)}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def ping(sid: str):
    """Heartbeat ping"""
    await sio.emit('pong', room=sid)


# ============================================================================
# BROADCAST HELPER FUNCTIONS (Called from API endpoints)
# ============================================================================

async def broadcast_to_user(user_id: int, event: str, data: dict):
    """
    Broadcast event to all connections of a specific user
    """
    try:
        room = f"user_{user_id}"
        await sio.emit(event, data, room=room)
        logger.info(f"Broadcasted {event} to user {user_id}: {data}")
    except Exception as e:
        logger.error(f"Broadcast error to user {user_id}: {str(e)}")


async def broadcast_to_team(team_id: int, event: str, data: dict):
    """
    Broadcast event to all members of a team
    """
    try:
        room = f"team_{team_id}"
        await sio.emit(event, data, room=room)
        logger.info(f"Broadcasted {event} to team {team_id}")
    except Exception as e:
        logger.error(f"Broadcast error to team {team_id}: {str(e)}")


async def broadcast_to_department(department: str, event: str, data: dict):
    """
    Broadcast event to all members of a department
    """
    try:
        room = f"dept_{department}"
        await sio.emit(event, data, room=room)
        logger.info(f"Broadcasted {event} to department {department}")
    except Exception as e:
        logger.error(f"Broadcast error to department {department}: {str(e)}")


async def broadcast_notification(user_id: int, notification_data: dict):
    """
    Broadcast new notification to user
    Event: 'new_notification'
    """
    await broadcast_to_user(user_id, 'new_notification', notification_data)


async def broadcast_approval_update(user_id: int, approval_data: dict):
    """
    Broadcast approval update to user
    Event: 'approval_updated'
    """
    await broadcast_to_user(user_id, 'approval_updated', approval_data)


async def broadcast_task_update(assignee_id: int, task_data: dict):
    """
    Broadcast task update to assignee
    Event: 'task_updated'
    """
    await broadcast_to_user(assignee_id, 'task_updated', task_data)


async def broadcast_task_status_change(task_id: int, status_data: dict):
    """
    Broadcast task status change to task owner and assignee
    Event: 'task_status_changed'
    """
    # Broadcast to assignee
    if 'assignee_id' in status_data:
        await broadcast_to_user(status_data['assignee_id'], 'task_status_changed', status_data)
    
    # Broadcast to assigner
    if 'assigner_id' in status_data:
        await broadcast_to_user(status_data['assigner_id'], 'task_status_changed', status_data)


async def broadcast_new_comment(task_id: int, comment_data: dict):
    """
    Broadcast new comment on task
    Event: 'new_comment'
    """
    # Broadcast to task participants (simplified - in production, query task participants)
    if 'assignee_id' in comment_data:
        await broadcast_to_user(comment_data['assignee_id'], 'new_comment', comment_data)
    if 'assigner_id' in comment_data:
        await broadcast_to_user(comment_data['assigner_id'], 'new_comment', comment_data)


async def broadcast_workload_alert(manager_id: int, alert_data: dict):
    """
    Broadcast workload alert to manager
    Event: 'workload_alert'
    """
    await broadcast_to_user(manager_id, 'workload_alert', alert_data)


# ============================================================================
# FASTAPI ROUTER (for REST endpoints related to WebSocket)
# ============================================================================

router = APIRouter(prefix="/websocket", tags=["WebSocket"])


@router.get("/status")
async def get_websocket_status():
    """Get WebSocket server status and connection count"""
    return {
        "status": "running",
        "active_connections": len(sid_to_user),
        "active_users": len(user_connections),
        "rooms": len(sio.manager.rooms.get("/", {})) if hasattr(sio.manager, 'rooms') else 0
    }


@router.post("/test-broadcast")
async def test_broadcast(user_id: int, message: str):
    """Test endpoint to send a broadcast to a specific user (for development)"""
    await broadcast_to_user(user_id, 'test_message', {'message': message})
    return {"status": "sent", "user_id": user_id, "message": message}


@router.get("/connections")
async def get_active_connections(current_user: User = Depends(get_current_user)):
    """Get list of active connections (admin only)"""
    if current_user.role != "ADMIN":
        return {"error": "Admin access required"}
    
    return {
        "total_connections": len(sid_to_user),
        "total_users": len(user_connections),
        "user_connections": {
            user_id: len(sids) 
            for user_id, sids in user_connections.items()
        }
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'sio',
    'socket_app',
    'router',
    'broadcast_to_user',
    'broadcast_to_team',
    'broadcast_to_department',
    'broadcast_notification',
    'broadcast_approval_update',
    'broadcast_task_update',
    'broadcast_task_status_change',
    'broadcast_new_comment',
    'broadcast_workload_alert',
]

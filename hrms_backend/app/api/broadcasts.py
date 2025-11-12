from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_async_session
from app.models import User, Employee
from app.core.security import get_current_active_user

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

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

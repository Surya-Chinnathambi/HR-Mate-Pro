from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_async_session
from app.core.security import get_current_user
from app.models import User, Employee
from app.services.additional_automation import ITHelpdeskAutomationService

router = APIRouter(prefix="/helpdesk", tags=["IT Helpdesk"])


class TicketCreate(BaseModel):
    issue_type: str
    description: str
    priority: str = "medium"  # low, medium, high


class AssetRequest(BaseModel):
    asset_type: str
    reason: str
    urgency: str = "normal"  # normal, urgent


@router.post("/suggest-solution")
async def get_automated_solution(
    issue_description: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get automated solution suggestion for common IT issues"""
    try:
        # Get automated solution (service doesn't need db or employee_id)
        solution = ITHelpdeskAutomationService.suggest_solution(
            issue_description=issue_description
        )
        
        return {
            "success": True,
            "data": solution,
            "message": "Solution suggestions retrieved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get solution: {str(e)}")


@router.post("/ticket")
async def create_it_ticket(
    ticket_data: TicketCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new IT support ticket"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Create ticket (service expects 'category' not 'issue_type')
        ticket = await ITHelpdeskAutomationService.create_ticket(
            db=session,
            employee_id=employee.id,
            category=ticket_data.issue_type,
            description=ticket_data.description,
            priority=ticket_data.priority
        )
        
        return {
            "success": True,
            "data": ticket,
            "message": "IT ticket created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")


@router.post("/asset-request")
async def request_it_asset(
    asset_data: AssetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Request IT hardware/equipment"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Create asset request (service expects 'justification' not 'reason')
        request = await ITHelpdeskAutomationService.request_asset(
            db=session,
            employee_id=employee.id,
            asset_type=asset_data.asset_type,
            justification=asset_data.reason
        )
        
        return {
            "success": True,
            "data": request,
            "message": "Asset request submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request asset: {str(e)}")

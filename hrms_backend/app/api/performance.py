from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.database import get_session
from app.core.security import get_current_user
from app.models import User, Employee
from app.services.additional_automation import PerformanceAutomationService

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/my-goals")
async def get_my_goals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get employee's performance goals and objectives"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get goals from automation service
        goals = await PerformanceAutomationService.get_my_goals(
            db=session,
            employee_id=employee.id
        )
        
        return {
            "success": True,
            "data": goals,
            "message": "Goals retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve goals: {str(e)}")


@router.put("/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: int,
    progress: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update progress on a specific goal"""
    try:
        # Validate progress
        if not 0 <= progress <= 100:
            raise HTTPException(status_code=400, detail="Progress must be between 0 and 100")
        
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Update goal progress
        result = await PerformanceAutomationService.update_goal_progress(
            db=session,
            employee_id=employee.id,
            goal_id=goal_id,
            progress=progress
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Goal progress updated to {progress}%"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update goal: {str(e)}")

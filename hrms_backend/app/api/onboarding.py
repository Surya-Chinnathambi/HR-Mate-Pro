from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.database import get_session
from app.core.security import get_current_user
from app.models import User, Employee
from app.services.additional_automation import OnboardingAutomationService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/checklist")
async def get_onboarding_checklist(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get employee's onboarding checklist with progress"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get onboarding checklist
        checklist = await OnboardingAutomationService.get_onboarding_checklist(
            db=session,
            employee_id=employee.id
        )
        
        return {
            "success": True,
            "data": checklist,
            "message": "Onboarding checklist retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve checklist: {str(e)}")


@router.put("/checklist/{item_id}")
async def update_checklist_item(
    item_id: int,
    completed: bool,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Mark an onboarding checklist item as complete/incomplete"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Update checklist item
        result = await OnboardingAutomationService.update_checklist_item(
            db=session,
            employee_id=employee.id,
            item_id=item_id,
            completed=completed
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Checklist item marked as {'complete' if completed else 'incomplete'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update checklist: {str(e)}")

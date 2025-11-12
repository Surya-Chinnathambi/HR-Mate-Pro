from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.database import get_session
from app.core.security import get_current_user
from app.models import User, Employee
from app.services.additional_automation import TrainingAutomationService

router = APIRouter(prefix="/training", tags=["Training"])


@router.get("/courses")
async def get_available_courses(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get available training courses for the employee"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get available courses
        courses = await TrainingAutomationService.get_available_courses(
            db=session,
            employee_id=employee.id
        )
        
        return {
            "success": True,
            "data": courses,
            "message": "Training courses retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve courses: {str(e)}")


@router.post("/courses/{course_id}/enroll")
async def enroll_in_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Enroll in a training course"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Enroll in course
        result = await TrainingAutomationService.enroll_in_course(
            db=session,
            employee_id=employee.id,
            course_id=course_id
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Successfully enrolled in course"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enroll in course: {str(e)}")

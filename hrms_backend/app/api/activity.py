from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_async_session
from app.models.user import User, Employee
from app.models.attendance import AttendanceDay, LeaveApplication, LeaveApplicationStatus
from app.core.security import get_current_active_user

router = APIRouter()


class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    time: str
    date: str
    icon: str
    color: str
    timestamp: datetime


@router.get("/feed", response_model=List[ActivityItem])
async def get_activity_feed(
    days: int = 7,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get user's recent activity feed"""
    # Get current employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    activities = []
    cutoff_date = date.today() - timedelta(days=days)
    
    # Get attendance activities (clock in/out)
    att_result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.employee_id == employee.id)
        .where(AttendanceDay.date >= cutoff_date)
        .order_by(AttendanceDay.date.desc())
        .limit(limit)
    )
    attendance_records = att_result.scalars().all()
    
    for att in attendance_records:
        if att.check_in:
            activities.append(ActivityItem(
                id=f"clock-in-{att.id}",
                type="clock-in",
                title="Clocked In",
                description=f"Started work session at {att.location_type or 'Office'}",
                time=att.check_in.strftime("%I:%M %p"),
                date=format_date(att.date),
                icon="LogIn",
                color="text-green-600 bg-green-50",
                timestamp=datetime.combine(att.date, att.check_in.time())
            ))
        
        if att.check_out:
            activities.append(ActivityItem(
                id=f"clock-out-{att.id}",
                type="clock-out",
                title="Clocked Out",
                description=f"Ended work session - {att.work_hours or 0:.1f}h worked",
                time=att.check_out.strftime("%I:%M %p"),
                date=format_date(att.date),
                icon="LogOut",
                color="text-red-600 bg-red-50",
                timestamp=datetime.combine(att.date, att.check_out.time())
            ))
    
    # Get leave application activities
    leave_result = await session.execute(
        select(LeaveApplication)
        .where(LeaveApplication.employee_id == employee.id)
        .where(LeaveApplication.applied_on >= cutoff_date)
        .order_by(LeaveApplication.applied_on.desc())
        .limit(10)
    )
    leave_applications = leave_result.scalars().all()
    
    for leave in leave_applications:
        if leave.status == LeaveApplicationStatus.APPROVED:
            activities.append(ActivityItem(
                id=f"leave-approved-{leave.id}",
                type="leave-approved",
                title="Leave Request Approved",
                description=f"{leave.leave_type} leave for {leave.from_date.strftime('%b %d')} - {leave.to_date.strftime('%b %d')}",
                time=leave.applied_on.strftime("%I:%M %p"),
                date=format_date(leave.applied_on.date()),
                icon="CheckCircle",
                color="text-blue-600 bg-blue-50",
                timestamp=leave.applied_on
            ))
        elif leave.status == LeaveApplicationStatus.REJECTED:
            activities.append(ActivityItem(
                id=f"leave-rejected-{leave.id}",
                type="leave-rejected",
                title="Leave Request Rejected",
                description=f"{leave.leave_type} leave - {leave.rejection_reason or 'No reason provided'}",
                time=leave.applied_on.strftime("%I:%M %p"),
                date=format_date(leave.applied_on.date()),
                icon="XCircle",
                color="text-red-600 bg-red-50",
                timestamp=leave.applied_on
            ))
        else:
            activities.append(ActivityItem(
                id=f"leave-pending-{leave.id}",
                type="leave-pending",
                title="Leave Request Submitted",
                description=f"{leave.leave_type} leave for {leave.from_date.strftime('%b %d')} - {leave.to_date.strftime('%b %d')}",
                time=leave.applied_on.strftime("%I:%M %p"),
                date=format_date(leave.applied_on.date()),
                icon="Clock",
                color="text-yellow-600 bg-yellow-50",
                timestamp=leave.applied_on
            ))
    
    # Sort all activities by timestamp (most recent first)
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Return limited results
    return activities[:limit]


@router.get("/stats")
async def get_activity_stats(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get activity statistics"""
    # Get current employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate stats for current month
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    # Count present days this month
    present_result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.employee_id == employee.id)
        .where(AttendanceDay.date >= month_start)
        .where(AttendanceDay.date <= today)
        .where(AttendanceDay.status.in_(['PRESENT', 'WORK_FROM_HOME']))
    )
    present_days = len(present_result.scalars().all())
    
    # Count total hours this month
    hours_result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.employee_id == employee.id)
        .where(AttendanceDay.date >= month_start)
        .where(AttendanceDay.date <= today)
    )
    attendance_records = hours_result.scalars().all()
    total_hours = sum(att.work_hours or 0 for att in attendance_records)
    avg_hours = total_hours / present_days if present_days > 0 else 0
    
    # Count pending leave applications
    pending_leaves_result = await session.execute(
        select(LeaveApplication)
        .where(LeaveApplication.employee_id == employee.id)
        .where(LeaveApplication.status == LeaveApplicationStatus.PENDING)
    )
    pending_leaves = len(pending_leaves_result.scalars().all())
    
    return {
        "present_days": present_days,
        "total_hours": round(total_hours, 1),
        "avg_hours": round(avg_hours, 1),
        "pending_leaves": pending_leaves,
        "month": today.strftime("%B %Y")
    }


def format_date(activity_date: date) -> str:
    """Format date for activity display"""
    today = date.today()
    diff = (today - activity_date).days
    
    if diff == 0:
        return "Today"
    elif diff == 1:
        return "Yesterday"
    elif diff < 7:
        return f"{diff} days ago"
    else:
        return activity_date.strftime("%b %d")

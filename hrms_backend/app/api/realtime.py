from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import List

from app.database import get_async_session
from app.models.user import User, Employee
from app.models.attendance import (
    AttendanceDay,
    AttendanceStatus,
    LeaveApplication,
    LeaveApplicationStatus,
    Holiday,
)
from app.models.extras import Notification
from app.core.security import get_current_active_user

router = APIRouter()

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get dashboard summary data"""
    # Get current employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get today's attendance
    today = date.today()
    att_result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.employee_id == employee.id)
        .where(AttendanceDay.date == today)
    )
    attendance = att_result.scalar_one_or_none()
    
    attendance_data = {
        "status": attendance.status.value if attendance else "Not Checked In",
        "checkIn": attendance.check_in.isoformat() if attendance and attendance.check_in else None,
        "checkOut": attendance.check_out.isoformat() if attendance and attendance.check_out else None,
        "workHours": attendance.work_hours if attendance else 0,
        "workLocation": attendance.location_type if attendance else "Office"
    }
    
    # Get upcoming holidays
    holidays_result = await session.execute(
        select(Holiday)
        .where(Holiday.date >= today)
        .where(Holiday.date <= today + timedelta(days=90))
        .order_by(Holiday.date)
        .limit(5)
    )
    upcoming_holidays = [
        {
            "_id": h.id,
            "name": h.name,
            "date": str(h.date),
            "isOptional": h.is_optional
        }
        for h in holidays_result.scalars().all()
    ]
    
    # Count team on leave
    leave_count_result = await session.execute(
    select(func.count(LeaveApplication.id))
    .where(LeaveApplication.status == LeaveApplicationStatus.APPROVED)
    .where(LeaveApplication.start_date <= today)
    .where(LeaveApplication.end_date >= today)
    )
    team_on_leave_count = leave_count_result.scalar() or 0
    
    # Count remote work
    remote_count_result = await session.execute(
    select(func.count(AttendanceDay.id))
    .where(AttendanceDay.date == today)
    .where(AttendanceDay.location_type == "remote")
    )
    remote_work_count = remote_count_result.scalar() or 0
    
    # Mock announcements (you can add a real Announcement model)
    announcements = [
        {
            "_id": 1,
            "title": "Welcome to HRMS",
            "content": "Manage your HR activities efficiently"
        }
    ]
    
    return {
        "attendance": attendance_data,
        "upcomingHolidays": upcoming_holidays,
        "teamOnLeaveCount": team_on_leave_count,
        "remoteWorkCount": remote_work_count,
        "announcements": announcements
    }

@router.get("/team-summary")
async def get_team_summary(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get team summary"""
    # Get current employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get all employees in same department
    team_result = await session.execute(
        select(Employee)
        .where(Employee.department == employee.department)
        .where(Employee.is_active == True)
    )
    team_members = team_result.scalars().all()
    
    # Get today's attendance for team
    today = date.today()
    attendance_result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.date == today)
        .where(AttendanceDay.employee_id.in_([e.id for e in team_members]))
    )
    attendances = {a.employee_id: a for a in attendance_result.scalars().all()}
    
    # Format team data
    team_data = []
    present_count = 0
    on_leave_count = 0
    wfh_count = 0
    
    for member in team_members:
        att = attendances.get(member.id)
        status = "Absent"
        if att:
            status = att.status.value
            if att.status == AttendanceStatus.PRESENT:
                present_count += 1
            elif att.status == AttendanceStatus.ON_LEAVE:
                on_leave_count += 1
            elif att.status == AttendanceStatus.WORK_FROM_HOME:
                wfh_count += 1
        
        team_data.append({
            "_id": member.id,
            "firstName": member.first_name,
            "lastName": member.last_name,
            "designation": member.designation,
            "attendanceStatus": status
        })
    
    return {
        "stats": {
            "total": len(team_members),
            "present": present_count,
            "onLeave": on_leave_count,
            "wfh": wfh_count
        },
        "team": team_data
    }

@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get notifications for current user"""
    # Get employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        return {"notifications": [], "unreadCount": 0}
    
    # Get notifications
    result = await session.execute(
        select(Notification)
        .where((Notification.employee_id == employee.id) | (Notification.employee_id == None))
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    
    unread_count = sum(1 for n in notifications if not n.is_read)
    
    return {
        "notifications": [
            {
                "_id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "isRead": n.is_read,
                "_creationTime": int(n.created_at.timestamp() * 1000)
            }
            for n in notifications
        ],
        "unreadCount": unread_count
    }

@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Mark notification as read"""
    result = await session.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.now()
    
    await session.commit()
    
    return {"message": "Notification marked as read"}

@router.get("/inbox-items")
async def get_inbox_items(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get inbox items (pending actions)"""
    # Get employee
    emp_result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = emp_result.scalar_one_or_none()
    
    # For now, return empty array - this would typically check for pending approvals
    return []

@router.get("/attendance-stats")
async def get_attendance_stats(
    employee_id: int,
    month: str,
    year: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get attendance statistics"""
    month_num = int(month)
    start_date = date(year, month_num, 1)
    if month_num == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month_num + 1, 1) - timedelta(days=1)
    
    result = await session.execute(
        select(AttendanceDay)
        .where(AttendanceDay.employee_id == employee_id)
        .where(AttendanceDay.date >= start_date)
        .where(AttendanceDay.date <= end_date)
    )
    attendances = result.scalars().all()
    
    present = sum(1 for a in attendances if a.status == AttendanceStatus.PRESENT)
    total_days = (end_date - start_date).days + 1
    attendance_percentage = (present / total_days * 100) if total_days > 0 else 0
    
    return {
        "present": present,
        "total": total_days,
        "attendancePercentage": round(attendance_percentage, 2)
    }
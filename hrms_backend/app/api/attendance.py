from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import Optional

from app.database import get_async_session
from app.models import User, Attendance, AttendanceStatus, Employee
from app.schemas import AttendanceResponse, AttendanceStats
from app.core.security import get_current_active_user

router = APIRouter()

def calculate_work_hours(check_in: datetime, check_out: datetime) -> float:
    """Calculate work hours between check-in and check-out"""
    if not check_in or not check_out:
        return 0.0
    delta = check_out - check_in
    return round(delta.total_seconds() / 3600, 2)

@router.post("/check-in")
async def check_in(
    employee_id: int,
    check_in_time: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Check in for attendance"""
    today = date.today()
    
    # Check if already checked in today
    result = await session.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee_id)
        .where(Attendance.date == today)
    )
    existing_attendance = result.scalar_one_or_none()
    
    if existing_attendance and existing_attendance.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in today"
        )
    
    # Parse check-in time
    if check_in_time:
        check_in_dt = datetime.strptime(f"{today} {check_in_time}", "%Y-%m-%d %H:%M")
    else:
        check_in_dt = datetime.now()
    
    if existing_attendance:
        # Update existing record
        existing_attendance.check_in = check_in_dt
        existing_attendance.status = AttendanceStatus.PRESENT
    else:
        # Create new attendance record
        attendance = Attendance(
            employee_id=employee_id,
            date=today,
            check_in=check_in_dt,
            status=AttendanceStatus.PRESENT
        )
        session.add(attendance)
    
    await session.commit()
    
    return {"message": "Checked in successfully", "check_in": check_in_dt}

@router.post("/check-out")
async def check_out(
    employee_id: int,
    check_out_time: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Check out for attendance"""
    today = date.today()
    
    # Get today's attendance
    result = await session.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee_id)
        .where(Attendance.date == today)
    )
    attendance = result.scalar_one_or_none()
    
    if not attendance or not attendance.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must check in before checking out"
        )
    
    if attendance.check_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked out today"
        )
    
    # Parse check-out time
    if check_out_time:
        check_out_dt = datetime.strptime(f"{today} {check_out_time}", "%Y-%m-%d %H:%M")
    else:
        check_out_dt = datetime.now()
    
    # Update attendance
    attendance.check_out = check_out_dt
    attendance.work_hours = calculate_work_hours(attendance.check_in, check_out_dt)
    
    await session.commit()
    await session.refresh(attendance)
    
    return {
        "message": "Checked out successfully",
        "check_out": check_out_dt,
        "work_hours": attendance.work_hours
    }

@router.get("/today")
async def get_today_attendance(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get today's attendance for employee"""
    today = date.today()
    
    # Get employee ID from user - use separate query to avoid lazy loading issues
    emp_result = await session.execute(
        select(Employee.id).where(Employee.user_id == current_user.id)
    )
    emp_id = emp_result.scalar_one_or_none()
    if not emp_id:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    result = await session.execute(
        select(Attendance)
        .where(Attendance.employee_id == emp_id)
        .where(Attendance.date == today)
    )
    attendance = result.scalar_one_or_none()
    
    if not attendance:
        return None
    
    return {
        "date": str(attendance.date),
        "checkIn": attendance.check_in.strftime("%H:%M") if attendance.check_in else None,
        "checkOut": attendance.check_out.strftime("%H:%M") if attendance.check_out else None,
        "workHours": attendance.work_hours,
        "status": attendance.status.value,
        "workLocation": attendance.location_type
    }

@router.get("/records")
async def get_attendance_records(
    limit: int = 100,
    employee_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get attendance records (paginated)"""
    # Get employee ID from user if not provided
    if not employee_id:
        emp_result = await session.execute(
            select(Employee.id).where(Employee.user_id == current_user.id)
        )
        employee_id = emp_result.scalar_one_or_none()
        if not employee_id:
            raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get attendance records
    result = await session.execute(
        select(Attendance)
        .where(Attendance.employee_id == employee_id)
        .order_by(Attendance.date.desc())
        .limit(limit)
    )
    attendances = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "date": str(a.date),
            "checkIn": a.check_in.strftime("%H:%M") if a.check_in else None,
            "checkOut": a.check_out.strftime("%H:%M") if a.check_out else None,
            "workHours": a.work_hours or 0,
            "status": a.status.value if hasattr(a.status, 'value') else str(a.status),
            "workLocation": a.location_type or "Office"
        }
        for a in attendances
    ]

@router.get("/stats")
async def get_attendance_stats(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get attendance statistics for a month"""
    # Use current month/year if not provided
    today = date.today()
    month_num = month if month is not None else today.month
    year_val = year if year is not None else today.year
    start_date = date(year_val, month_num, 1)
    if month_num == 12:
        end_date = date(year_val + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year_val, month_num + 1, 1) - timedelta(days=1)
    
    # Get employee ID from user - use separate query to avoid lazy loading issues
    emp_result = await session.execute(
        select(Employee.id).where(Employee.user_id == current_user.id)
    )
    emp_id = emp_result.scalar_one_or_none()
    if not emp_id:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Get all attendance records for the month
    result = await session.execute(
        select(Attendance)
        .where(Attendance.employee_id == emp_id)
        .where(Attendance.date >= start_date)
        .where(Attendance.date <= end_date)
    )
    attendances = result.scalars().all()
    
    # Calculate statistics
    present = sum(1 for a in attendances if a.status == AttendanceStatus.PRESENT)
    absent = sum(1 for a in attendances if a.status == AttendanceStatus.ABSENT)
    on_leave = sum(1 for a in attendances if a.status == AttendanceStatus.ON_LEAVE)
    half_day = sum(1 for a in attendances if a.status == AttendanceStatus.HALF_DAY)
    wfh = sum(1 for a in attendances if a.status == AttendanceStatus.WFH)
    
    # Calculate average hours
    total_hours = sum(a.work_hours or 0 for a in attendances if a.work_hours)
    avg_hours = (total_hours / len(attendances)) if attendances else 0
    
    total_days = (end_date - start_date).days + 1
    working_days = total_days  # Simplified, should exclude weekends and holidays
    attendance_percentage = (present / working_days * 100) if working_days > 0 else 0
    
    return {
        "present": present,
        "absent": absent,
        "onLeave": on_leave,
        "halfDay": half_day,
        "wfh": wfh,
        "attendancePercentage": round(attendance_percentage, 2),
        "average_hours_per_day": round(avg_hours, 2),
        "total_hours": round(total_hours, 2),
        "working_days": working_days
    }

@router.get("/history")
async def get_attendance_history(
    employee_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get attendance history for employee"""
    query = select(Attendance).where(Attendance.employee_id == employee_id)
    
    if start_date:
        query = query.where(Attendance.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    
    if end_date:
        query = query.where(Attendance.date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    
    query = query.order_by(Attendance.date.desc())
    
    result = await session.execute(query)
    attendances = result.scalars().all()
    
    return [
        {
            "id": a.id,
            "date": str(a.date),
            "checkIn": a.check_in.strftime("%H:%M") if a.check_in else None,
            "checkOut": a.check_out.strftime("%H:%M") if a.check_out else None,
            "workHours": a.work_hours,
            "status": a.status.value,
            "workLocation": a.location_type
        }
        for a in attendances
    ]
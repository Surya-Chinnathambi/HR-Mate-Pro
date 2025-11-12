from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from typing import List

from app.database import get_async_session
from app.models import User, Leave, LeaveType, LeaveBalance, LeaveStatus, Employee
from app.schemas import LeaveCreate, LeaveResponse
from app.core.security import get_current_active_user

router = APIRouter()

def calculate_days(start_date: date, end_date: date) -> int:
    """Calculate number of days between dates"""
    return (end_date - start_date).days + 1

@router.get("/types")
async def get_leave_types(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all leave types"""
    result = await session.execute(select(LeaveType))
    leave_types = result.scalars().all()
    
    return [
        {
            "_id": lt.id,
            "name": lt.name,
            "code": lt.code,
            "description": lt.description,
            "maxDaysPerYear": lt.max_days_per_year,
            "isPaid": lt.is_paid
        }
        for lt in leave_types
    ]

@router.post("/apply")
async def apply_leave(
    leave_data: LeaveCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Apply for leave"""
    # Get leave type by name/code
    result = await session.execute(
        select(LeaveType).where(
            (LeaveType.code == leave_data.leave_type) |
            (LeaveType.name == leave_data.leave_type)
        )
    )
    leave_type = result.scalar_one_or_none()
    
    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave type '{leave_data.leave_type}' not found"
        )
    
    # Calculate total days
    total_days = calculate_days(leave_data.start_date, leave_data.end_date)
    
    # Check leave balance
    balance_result = await session.execute(
        select(LeaveBalance)
        .where(LeaveBalance.employee_id == leave_data.employee_id)
        .where(LeaveBalance.leave_type_id == leave_type.id)
        .where(LeaveBalance.year == datetime.now().year)
    )
    balance = balance_result.scalar_one_or_none()
    
    if balance and balance.balance < total_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient leave balance. Available: {balance.balance} days"
        )
    
    # Create leave application
    leave = Leave(
        employee_id=leave_data.employee_id,
        leave_type_id=leave_type.id,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        total_days=total_days,
        reason=leave_data.reason,
        status=LeaveStatus.PENDING,
        applied_date=datetime.now()
    )
    
    session.add(leave)
    await session.commit()
    await session.refresh(leave)
    
    return {
        "message": "Leave application submitted successfully",
        "leaveId": leave.id,
        "status": leave.status.value
    }

@router.get("/balance")
async def get_leave_balance(
    employee_id: int,
    year: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get leave balance for employee"""
    # Get all leave types
    leave_types_result = await session.execute(select(LeaveType))
    leave_types = leave_types_result.scalars().all()
    
    balances = []
    for lt in leave_types:
        # Get or create balance
        balance_result = await session.execute(
            select(LeaveBalance)
            .where(LeaveBalance.employee_id == employee_id)
            .where(LeaveBalance.leave_type_id == lt.id)
            .where(LeaveBalance.year == year)
        )
        balance = balance_result.scalar_one_or_none()
        
        if not balance:
            # Create default balance
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type_id=lt.id,
                year=year,
                opening=lt.max_days_per_year,
                accrued=lt.max_days_per_year,
                consumed=0,
                balance=lt.max_days_per_year
            )
            session.add(balance)
            await session.commit()
            await session.refresh(balance)
        
        # Get pending leaves
        pending_result = await session.execute(
            select(Leave)
            .where(Leave.employee_id == employee_id)
            .where(Leave.leave_type_id == lt.id)
            .where(Leave.status == LeaveStatus.PENDING)
        )
        pending_leaves = pending_result.scalars().all()
        pending_days = sum(l.total_days for l in pending_leaves)
        
        utilization = (balance.consumed / balance.accrued * 100) if balance.accrued > 0 else 0
        
        balances.append({
            "leaveType": {
                "_id": lt.id,
                "name": lt.name,
                "code": lt.code
            },
            "balance": {
                "opening": balance.opening,
                "accrued": balance.accrued,
                "consumed": balance.consumed,
                "balance": balance.balance
            },
            "isLowBalance": balance.balance < 3,
            "utilizationPercentage": round(utilization, 2),
            "pendingDays": pending_days
        })
    
    return balances

@router.get("/applications")
async def get_leave_applications(
    employee_id: int,
    status: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get leave applications for employee"""
    query = select(Leave).where(Leave.employee_id == employee_id)
    
    if status:
        query = query.where(Leave.status == status)
    
    query = query.order_by(Leave.applied_date.desc())
    
    result = await session.execute(query)
    leaves = result.scalars().all()
    
    # Get leave types
    leave_type_result = await session.execute(select(LeaveType))
    leave_types = {lt.id: lt for lt in leave_type_result.scalars().all()}
    
    return [
        {
            "_id": l.id,
            "employeeId": l.employee_id,
            "leaveType": {
                "_id": leave_types[l.leave_type_id].id,
                "name": leave_types[l.leave_type_id].name,
                "code": leave_types[l.leave_type_id].code
            } if l.leave_type_id in leave_types else None,
            "startDate": str(l.start_date),
            "endDate": str(l.end_date),
            "totalDays": l.total_days,
            "reason": l.reason,
            "status": l.status.value,
            "appliedDate": l.applied_date.isoformat(),
            "approverComments": l.approver_comments
        }
        for l in leaves
    ]

@router.put("/{leave_id}/approve")
async def approve_leave(
    leave_id: int,
    comments: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Approve leave application"""
    result = await session.execute(
        select(Leave).where(Leave.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave application not found"
        )
    
    leave.status = LeaveStatus.APPROVED
    leave.approver_comments = comments
    leave.approved_date = datetime.now()
    
    # Update leave balance
    balance_result = await session.execute(
        select(LeaveBalance)
        .where(LeaveBalance.employee_id == leave.employee_id)
        .where(LeaveBalance.leave_type_id == leave.leave_type_id)
        .where(LeaveBalance.year == datetime.now().year)
    )
    balance = balance_result.scalar_one_or_none()
    
    if balance:
        balance.consumed += leave.total_days
        balance.balance = balance.accrued - balance.consumed
    
    await session.commit()
    
    return {"message": "Leave approved successfully"}

@router.put("/{leave_id}/reject")
async def reject_leave(
    leave_id: int,
    comments: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Reject leave application"""
    result = await session.execute(
        select(Leave).where(Leave.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave application not found"
        )
    
    leave.status = LeaveStatus.REJECTED
    leave.approver_comments = comments
    leave.approved_date = datetime.now()
    
    await session.commit()
    
    return {"message": "Leave rejected"}
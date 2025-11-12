from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List

from app.database import get_async_session
from app.models import User, Payroll, Employee
from app.schemas import PayrollCreate, PayrollResponse
from app.core.security import get_current_active_user

router = APIRouter()

@router.post("/generate", response_model=PayrollResponse)
async def generate_payroll(
    payroll_data: PayrollCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate payroll for an employee"""
    # Get employee
    emp_result = await session.execute(
        select(Employee).where(Employee.id == payroll_data.employee_id)
    )
    employee = emp_result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Calculate net pay
    net_pay = payroll_data.gross_pay - payroll_data.deductions
    
    # Parse period to get month and year
    month_year = payroll_data.period.split()
    month_name = month_year[0]
    year = int(month_year[1])
    
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    month = month_map.get(month_name, 1)
    
    # Create payroll record
    payroll = Payroll(
        employee_id=payroll_data.employee_id,
        period=payroll_data.period,
        month=month,
        year=year,
        gross_pay=payroll_data.gross_pay,
        deductions=payroll_data.deductions,
        net_pay=net_pay,
        status="Paid",
        payment_date=datetime.now().date()
    )
    
    session.add(payroll)
    await session.commit()
    await session.refresh(payroll)
    
    return payroll

@router.get("/history", response_model=List[PayrollResponse])
async def get_payroll_history(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get payroll history for employee"""
    result = await session.execute(
        select(Payroll)
        .where(Payroll.employee_id == employee_id)
        .order_by(Payroll.year.desc(), Payroll.month.desc())
    )
    payrolls = result.scalars().all()
    
    return payrolls

@router.get("/{payroll_id}", response_model=PayrollResponse)
async def get_payroll(
    payroll_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get payroll by ID"""
    result = await session.execute(
        select(Payroll).where(Payroll.id == payroll_id)
    )
    payroll = result.scalar_one_or_none()
    
    if not payroll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    return payroll
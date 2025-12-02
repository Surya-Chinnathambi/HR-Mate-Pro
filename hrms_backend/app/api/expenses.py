"""
Expenses API
Endpoints for expense management and approvals
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_async_session
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseCreate(BaseModel):
    category: str
    amount: float
    currency: str = "USD"
    description: str
    date: str
    receipt_url: Optional[str] = None


class ExpenseStats(BaseModel):
    total_expenses: int
    total_amount: float
    pending_amount: float
    approved_amount: float
    reimbursed_amount: float
    rejected_count: int


@router.get("/")
async def get_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get user's expenses"""
    try:
        # Get employee_id
        emp_query = text("SELECT id FROM employees WHERE user_id = :user_id")
        emp_result = await db.execute(emp_query, {"user_id": current_user.id})
        employee = emp_result.fetchone()
        
        if not employee:
            return {"expenses": [], "total": 0}
        
        employee_id = employee[0]
        
        # Build query
        conditions = ["employee_id = :employee_id"]
        params = {"employee_id": employee_id, "skip": skip, "limit": limit}
        
        if status:
            conditions.append("status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(conditions)
        
        # Placeholder - actual expenses table may differ
        # This returns empty for now until expenses table is confirmed
        return {
            "expenses": [],
            "total": 0,
            "message": "Expenses feature coming soon"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expenses: {str(e)}"
        )


@router.get("/stats", response_model=ExpenseStats)
async def get_expense_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get expense statistics"""
    # Placeholder
    return ExpenseStats(
        total_expenses=0,
        total_amount=0.0,
        pending_amount=0.0,
        approved_amount=0.0,
        reimbursed_amount=0.0,
        rejected_count=0
    )


@router.get("/pending-approvals")
async def get_pending_approvals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get expenses pending approval (for managers)"""
    return {
        "expenses": [],
        "total": 0,
        "message": "Expenses approval feature coming soon"
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new expense"""
    return {
        "message": "Expense creation feature coming soon",
        "expense": expense.dict()
    }


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Approve an expense"""
    return {"message": "Expense approval feature coming soon"}


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: int,
    comments: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Reject an expense"""
    return {"message": "Expense rejection feature coming soon"}

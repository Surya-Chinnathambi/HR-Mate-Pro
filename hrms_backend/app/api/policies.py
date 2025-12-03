from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_async_session
from app.models import User, Policy, Employee
from app.core.security import get_current_active_user
from app.services.additional_automation import PolicyAutomationService

router = APIRouter()

@router.get("/policies")
async def get_policies(
    category: str = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all company policies"""
    query = select(Policy).where(Policy.is_active == True)
    
    if category:
        query = query.where(Policy.category == category)
    
    query = query.order_by(Policy.category, Policy.title)
    
    result = await session.execute(query)
    policies = result.scalars().all()
    
    return [
        {
            "policy_id": str(p.id),
            "id": str(p.id),  # Keep for backwards compatibility
            "title": p.title,
            "description": p.content[:200] if p.content else "",  # First 200 chars as description
            "category": p.category,
            "content": p.content,
            "version": p.version,
            "effective_date": p.created_at.isoformat(),
            "created_by": str(p.created_by) if hasattr(p, 'created_by') else "",
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat() if p.updated_at else p.created_at.isoformat(),
            "lastUpdated": p.updated_at.isoformat() if p.updated_at else p.created_at.isoformat(),
            "requires_acknowledgment": True,
            "acknowledged": False  # TODO: Check user acknowledgments from database
        }
        for p in policies
    ]

@router.get("/policies/categories")
async def get_policy_categories(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all policy categories"""
    try:
        result = await session.execute(
            select(Policy.category).distinct().where(Policy.is_active == True)
        )
        categories = [row[0] for row in result.all()]
        
        return {
            "categories": categories,
            "total": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")


@router.get("/policies/stats")
async def get_policy_stats(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get policy statistics"""
    try:
        # Get total policies
        total_result = await session.execute(
            select(Policy).where(Policy.is_active == True)
        )
        total_policies = len(total_result.scalars().all())
        
        # Get policies by category
        category_result = await session.execute(
            select(Policy.category).where(Policy.is_active == True)
        )
        categories = {}
        for row in category_result.all():
            cat = row[0]
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_policies": total_policies,
            "by_category": categories,
            "categories_count": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@router.get("/policies/search")
async def search_policies(
    query: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Search policies by keyword (using automation service)"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Search policies
        policies = await PolicyAutomationService.search_policy(
            db=session,
            employee_id=employee.id,
            search_query=query or ""
        )
        
        return {
            "success": True,
            "data": policies,
            "message": "Policy search completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search policies: {str(e)}")


@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get policy by ID"""
    result = await session.execute(
        select(Policy).where(Policy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {
        "id": str(policy.id),
        "title": policy.title,
        "category": policy.category,
        "content": policy.content,
        "version": policy.version,
        "lastUpdated": policy.updated_at.isoformat() if policy.updated_at else policy.created_at.isoformat()
    }


@router.get("/policies/{policy_id}/details")
async def get_policy_details(
    policy_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get detailed policy information (using automation service)"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get policy details
        policy_details = await PolicyAutomationService.get_policy_details(
            db=session,
            employee_id=employee.id,
            policy_id=policy_id
        )
        
        return {
            "success": True,
            "data": policy_details,
            "message": "Policy details retrieved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get policy details: {str(e)}")

"""
Organization API
Endpoints for organization structure, departments, and hierarchy
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_async_session
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/organization", tags=["organization"])


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    head_id: Optional[int] = None
    head_name: Optional[str] = None
    employee_count: int = 0


class EmployeeNode(BaseModel):
    id: int
    employee_id: str
    first_name: str
    last_name: str
    email: str
    designation: str
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_manager: bool = False
    subordinates: List['EmployeeNode'] = []


@router.get("/departments", response_model=List[DepartmentResponse])
async def get_departments(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get all departments with employee counts"""
    try:
        query = text("""
            SELECT 
                d.id,
                d.name,
                d.description,
                d.head_id,
                CONCAT(e.first_name, ' ', e.last_name) as head_name,
                COUNT(DISTINCT emp.id) as employee_count
            FROM departments d
            LEFT JOIN employees e ON d.head_id = e.id
            LEFT JOIN employees emp ON emp.department_id = d.id AND emp.is_deleted = false
            WHERE d.is_deleted = false
            GROUP BY d.id, d.name, d.description, d.head_id, e.first_name, e.last_name
            ORDER BY d.name
        """)
        
        result = await db.execute(query)
        departments = result.fetchall()
        
        return [
            DepartmentResponse(
                id=dept[0],
                name=dept[1],
                description=dept[2],
                head_id=dept[3],
                head_name=dept[4],
                employee_count=dept[5]
            )
            for dept in departments
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch departments: {str(e)}"
        )


@router.get("/tree")
async def get_organization_tree(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get organization hierarchy tree"""
    try:
        # Get all active employees
        query = text("""
            SELECT 
                id, employee_id, first_name, last_name, email,
                designation, department_id, manager_id, is_manager
            FROM employees
            WHERE is_deleted = false AND is_active = true
            ORDER BY manager_id NULLS FIRST, first_name
        """)
        
        result = await db.execute(query)
        employees = result.fetchall()
        
        # Build employee map
        emp_map = {}
        for emp in employees:
            emp_map[emp[0]] = {
                "id": emp[0],
                "employee_id": emp[1],
                "first_name": emp[2],
                "last_name": emp[3],
                "email": emp[4],
                "designation": emp[5],
                "department_id": emp[6],
                "manager_id": emp[7],
                "is_manager": emp[8],
                "subordinates": []
            }
        
        # Build tree structure
        tree = []
        for emp_id, emp_data in emp_map.items():
            manager_id = emp_data["manager_id"]
            if manager_id and manager_id in emp_map:
                emp_map[manager_id]["subordinates"].append(emp_data)
            elif not manager_id:
                # Top level employee (no manager)
                tree.append(emp_data)
        
        return tree
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch organization tree: {str(e)}"
        )

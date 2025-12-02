from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import selectinload
from typing import List, Optional
import os
import shutil
from pathlib import Path
import uuid
from datetime import datetime

from app.database import get_async_session
from app.models import User, Employee, Department, Location
from app.schemas import EmployeeResponse, EmployeeUpdate
from app.core.security import get_current_active_user

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/current", response_model=EmployeeResponse)
async def get_current_employee(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current employee profile"""
    # Eagerly load department and location to avoid lazy loading issues
    result = await session.execute(
        select(Employee)
        .options(
            selectinload(Employee.department),
            selectinload(Employee.location)
        )
        .where(Employee.user_id == current_user.id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    # Convert to dict and populate string fields from relationships
    emp_dict = {
        "id": employee.id,
        "employee_id": employee.employee_id,
        "first_name": employee.first_name,
        "middle_name": employee.middle_name,
        "last_name": employee.last_name,
        "display_name": employee.display_name,
        "email": employee.email,
        "phone": employee.phone,
        "designation": employee.designation,
        "department": employee.department.name if employee.department else None,
        "location": employee.location.name if employee.location else None,
        "salary": employee.salary,
        "date_of_birth": employee.date_of_birth,
        "gender": employee.gender,
        "role": employee.role,
        "team_id": employee.team_id,
        "is_active": employee.is_active,
        "created_at": employee.created_at,
        "updated_at": employee.updated_at,
    }
    
    return emp_dict

@router.get("/teammates", response_model=List[EmployeeResponse])
async def get_teammates(
    department: str = None,
    exclude_id: int = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get team members in the same department"""
    # Get current employee's department if not provided
    if department is None or exclude_id is None:
        emp_result = await session.execute(
            select(Employee).where(Employee.user_id == current_user.id)
        )
        current_emp = emp_result.scalar_one_or_none()
        if not current_emp:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        department = department or current_emp.department
        exclude_id = exclude_id or current_emp.id
    
    result = await session.execute(
        select(Employee)
        .where(Employee.department == department)
        .where(Employee.id != exclude_id)
        .where(Employee.is_active == True)
    )
    teammates = result.scalars().all()
    return teammates

@router.get("/organization-tree")
async def get_organization_tree(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get organization structure by department"""
    # Get all active employees with their departments using raw SQL
    query = text("""
        SELECT 
            e.id,
            e.employee_id,
            e.first_name,
            e.last_name,
            e.designation,
            e.email,
            COALESCE(d.name, 'Unassigned') as department_name,
            e.department_id
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.is_active = true
        ORDER BY d.name, e.first_name
    """)
    
    result = await session.execute(query)
    employees = result.fetchall()
    
    # Group by department
    org_tree = {}
    for emp in employees:
        dept_name = emp[6]  # department_name
        if dept_name not in org_tree:
            org_tree[dept_name] = []
        org_tree[dept_name].append({
            "_id": emp[0],
            "employeeId": emp[1],
            "firstName": emp[2],
            "lastName": emp[3],
            "designation": emp[4],
            "email": emp[5]
        })
    
    # Format response
    tree = []
    for dept, emps in org_tree.items():
        tree.append({
            "department": dept,
            "count": len(emps),
            "employees": emps
        })
    
    return tree

@router.get("/directory")
async def get_employee_directory(
    search: Optional[str] = None,
    department: Optional[str] = None,
    location_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get employee directory with filters"""
    # Use raw SQL to get employees with department names
    query_sql = """
        SELECT 
            e.id,
            e.employee_id,
            e.first_name,
            e.last_name,
            e.designation,
            e.department_id,
            d.name as department_name,
            e.location_id,
            e.email,
            e.phone
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.is_active = true
    """
    
    params = {}
    
    if search:
        query_sql += " AND (e.first_name ILIKE :search OR e.last_name ILIKE :search OR e.email ILIKE :search)"
        params["search"] = f"%{search}%"
    
    if department:
        query_sql += " AND d.name = :department"
        params["department"] = department
    
    if location_id:
        query_sql += " AND e.location_id = :location_id"
        params["location_id"] = location_id
    
    query_sql += " ORDER BY e.first_name, e.last_name"
    
    result = await session.execute(text(query_sql), params)
    employees = result.fetchall()
    
    # Get unique departments and location_ids for filters
    filter_query = text("""
        SELECT DISTINCT d.name as department_name, e.location_id
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.is_active = true AND (d.name IS NOT NULL OR e.location_id IS NOT NULL)
    """)
    
    filter_result = await session.execute(filter_query)
    filter_data = filter_result.fetchall()
    
    departments = list(set([row[0] for row in filter_data if row[0]]))
    location_ids = list(set([row[1] for row in filter_data if row[1]]))
    
    return {
        "employees": [
            {
                "_id": row[0],
                "employeeId": row[1],
                "firstName": row[2],
                "lastName": row[3],
                "designation": row[4],
                "department_id": row[5],
                "department": row[6],
                "location_id": row[7],
                "email": row[8],
                "phone": row[9]
            }
            for row in employees
        ],
        "filters": {
            "departments": sorted(departments),
            "location_ids": sorted(location_ids)
        }
    }

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update employee profile"""
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update fields
    update_data = employee_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)
    
    await session.commit()
    await session.refresh(employee)
    
    return employee

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get employee by ID"""
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upload employee profile avatar"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WebP images are allowed"
        )
    
    # Validate file size (max 5MB)
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    for chunk in iter(lambda: file.file.read(chunk_size), b""):
        file_size += len(chunk)
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 5MB"
            )
    
    # Reset file pointer
    file.file.seek(0)
    
    # Get current employee
    result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Update employee avatar URL
    avatar_url = f"/uploads/avatars/{unique_filename}"
    employee.avatar = avatar_url
    
    await session.commit()
    await session.refresh(employee)
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }

@router.get("/all/list")
async def get_all_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    is_manager: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all employees with pagination and filters"""
    # Use raw SQL to avoid relationship loading issues
    query_sql = """
        SELECT 
            e.id,
            e.employee_id,
            e.first_name,
            e.last_name,
            e.display_name,
            e.email,
            e.phone,
            e.designation,
            e.department_id,
            d.name as department_name,
            e.location_id,
            l.name as location_name,
            e.is_manager,
            e.is_active,
            e.date_of_joining
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE e.is_active = true
    """
    
    params = {}
    
    if search:
        query_sql += " AND (e.first_name ILIKE :search OR e.last_name ILIKE :search OR e.email ILIKE :search OR e.employee_id ILIKE :search)"
        params["search"] = f"%{search}%"
    
    if department_id:
        query_sql += " AND e.department_id = :department_id"
        params["department_id"] = department_id
    
    if is_manager is not None:
        query_sql += " AND e.is_manager = :is_manager"
        params["is_manager"] = is_manager
    
    query_sql += " ORDER BY e.first_name LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    result = await session.execute(text(query_sql), params)
    employees = result.fetchall()
    
    return [
        {
            "id": row[0],
            "employee_id": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "display_name": row[4],
            "email": row[5],
            "phone": row[6],
            "designation": row[7],
            "department_id": row[8],
            "department_name": row[9],
            "location_id": row[10],
            "location_name": row[11],
            "is_manager": row[12],
            "is_active": row[13],
            "date_of_joining": row[14].isoformat() if row[14] else None
        }
        for row in employees
    ]
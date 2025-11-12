from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
import shutil
from pathlib import Path
import uuid
from datetime import datetime

from app.database import get_async_session
from app.models import User, Employee
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
    result = await session.execute(
        select(Employee).where(Employee.user_id == current_user.id)
    )
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    return employee

@router.get("/teammates", response_model=List[EmployeeResponse])
async def get_teammates(
    department: str,
    exclude_id: int,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get team members in the same department"""
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
    result = await session.execute(
        select(Employee)
        .where(Employee.is_active == True)
        .order_by(Employee.department)
    )
    employees = result.scalars().all()
    
    # Group by department
    org_tree = {}
    for emp in employees:
        if emp.department not in org_tree:
            org_tree[emp.department] = []
        org_tree[emp.department].append(emp)
    
    # Format response
    tree = []
    for dept, emps in org_tree.items():
        tree.append({
            "department": dept,
            "count": len(emps),
            "employees": [
                {
                    "_id": emp.id,
                    "employeeId": emp.employee_id,
                    "firstName": emp.first_name,
                    "lastName": emp.last_name,
                    "designation": emp.designation,
                    "email": emp.email
                }
                for emp in emps
            ]
        })
    
    return tree

@router.get("/directory")
async def get_employee_directory(
    search: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get employee directory with filters"""
    query = select(Employee).where(Employee.is_active == True)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Employee.first_name.ilike(search_filter)) |
            (Employee.last_name.ilike(search_filter)) |
            (Employee.email.ilike(search_filter))
        )
    
    if department:
        query = query.where(Employee.department == department)
    
    if location:
        query = query.where(Employee.location == location)
    
    result = await session.execute(query)
    employees = result.scalars().all()
    
    # Get unique departments and locations for filters
    all_employees = await session.execute(select(Employee).where(Employee.is_active == True))
    all_emps = all_employees.scalars().all()
    
    departments = list(set([e.department for e in all_emps if e.department]))
    locations = list(set([e.location for e in all_emps if e.location]))
    
    return {
        "employees": [
            {
                "_id": emp.id,
                "employeeId": emp.employee_id,
                "firstName": emp.first_name,
                "lastName": emp.last_name,
                "designation": emp.designation,
                "department": emp.department,
                "location": emp.location,
                "email": emp.email,
                "phone": emp.phone
            }
            for emp in employees
        ],
        "filters": {
            "departments": departments,
            "locations": locations
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

@router.get("/all/list", response_model=List[EmployeeResponse])
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
    query = select(Employee).where(Employee.is_active == True)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Employee.first_name.ilike(search_filter),
                Employee.last_name.ilike(search_filter),
                Employee.email.ilike(search_filter),
                Employee.employee_id.ilike(search_filter)
            )
        )
    
    if department_id:
        query = query.where(Employee.department_id == department_id)
    
    if is_manager is not None:
        query = query.where(Employee.is_manager == is_manager)
    
    query = query.offset(skip).limit(limit).order_by(Employee.first_name)
    
    result = await session.execute(query)
    employees = result.scalars().all()
    
    return employees
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee
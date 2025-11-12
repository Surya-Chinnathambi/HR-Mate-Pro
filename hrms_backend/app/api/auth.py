from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.database import get_async_session
from app.models import User, Employee
from app.models.user import UserStatus
from app.schemas import Token, UserLogin, UserRegister, EmployeeResponse
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_current_active_user
)
from app.config import settings

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(
    user_data: UserRegister,
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new user"""
    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Create employee record
    from datetime import date as date_type
    employee = Employee(
        user_id=user.id,
        employee_id=f"EMP{str(user.id).zfill(4)}",
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        display_name=f"{user_data.first_name} {user_data.last_name}",
        email=user_data.email,
        designation="Employee",
        employment_type="full_time",
        currency="INR",
        date_of_joining=date_type.today()
    )
    session.add(employee)
    await session.commit()
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    """Login user"""
    result = await session.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """Refresh access token"""
    access_token = create_access_token(data={"sub": current_user.email})
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=EmployeeResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current user's employee profile"""
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

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user (client should delete token)"""
    return {"message": "Successfully logged out"}
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str

# Employee Schemas
class EmployeeBase(BaseModel):
    employee_id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    display_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    designation: str
    department: Optional[str] = None  # Changed to Optional to match model
    location: Optional[str] = None
    salary: Optional[float] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    role: str = "employee"  # Role-based access: 'employee', 'manager', 'hr'
    team_id: Optional[int] = None  # Team assignment for managers and employees

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Attendance Schemas
class AttendanceBase(BaseModel):
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = "Present"
    work_location: str = "Office"

class AttendanceCreate(BaseModel):
    employee_id: int
    check_in_time: Optional[str] = None

class AttendanceUpdate(BaseModel):
    check_out_time: Optional[str] = None
    status: Optional[str] = None

class AttendanceResponse(AttendanceBase):
    id: int
    employee_id: int
    work_hours: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceStats(BaseModel):
    present: int
    absent: int
    on_leave: int
    half_day: int
    wfh: int
    attendance_percentage: float

# Leave Schemas
class LeaveBase(BaseModel):
    start_date: date
    end_date: date
    reason: str

class LeaveCreate(LeaveBase):
    employee_id: int
    leave_type: str  # This will be converted to leave_type_id

class LeaveUpdate(BaseModel):
    status: Optional[str] = None
    approver_comments: Optional[str] = None

class LeaveResponse(LeaveBase):
    id: int
    employee_id: int
    total_days: int
    status: str
    applied_date: datetime
    
    class Config:
        from_attributes = True

class LeaveBalanceResponse(BaseModel):
    leave_type: dict
    balance: dict
    is_low_balance: bool
    utilization_percentage: float
    pending_days: int

# Payroll Schemas
class PayrollCreate(BaseModel):
    employee_id: int
    period: str
    gross_pay: float
    deductions: float = 0

class PayrollResponse(BaseModel):
    id: int
    employee_id: int
    period: str
    gross_pay: float
    deductions: float
    net_pay: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Dashboard Schemas
class DashboardSummary(BaseModel):
    attendance: dict
    upcoming_holidays: List[dict]
    team_on_leave_count: int
    remote_work_count: int
    announcements: List[dict]

class TeamSummary(BaseModel):
    stats: dict
    team: List[dict]

# Notification Schemas
class NotificationCreate(BaseModel):
    employee_id: Optional[int] = None
    title: str
    message: str
    type: str = "info"
    priority: str = "medium"

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    priority: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# AI Schemas
class AIRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    employee_id: int

class AIResponse(BaseModel):
    response: str
    timestamp: datetime
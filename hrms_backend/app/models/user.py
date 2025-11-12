"""
app/models/user.py and app/models/employee.py

These models define your database tables. SQLModel is beautiful because
it serves three purposes:
1. Defines the database table structure (like traditional ORMs)
2. Validates data with Pydantic
3. Can be used directly in API responses

Think of these as the "blueprint" for your data.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import Index
from enum import Enum

if TYPE_CHECKING:
    from app.models.chat import ChatConversation
    from app.models.extras import Payroll


# ============================================================================
# ENUMS - Define valid choices for certain fields
# ============================================================================

class UserRole(str, Enum):
    """User roles define what permissions a user has"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    PAYROLL_ADMIN = "payroll_admin"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Gender(str, Enum):
    """Gender options"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


# ============================================================================
# USER MODEL - Authentication and account management
# ============================================================================

class User(SQLModel, table=True):
    """
    User model for authentication.
    
    This is separate from Employee because:
    - A user might not be an employee (admin accounts, system accounts)
    - Separating concerns (auth vs HR data)
    - Better security (password hash is isolated)
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    
    # SSO Integration (Azure AD, Google, etc.)
    sso_id: Optional[str] = Field(default=None, unique=True, index=True)
    sso_provider: Optional[str] = Field(default=None, max_length=50)
    
    # Access Control
    role: UserRole = Field(default=UserRole.EMPLOYEE)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    
    # Audit fields - These track when records are created/modified
    # Very important for compliance and debugging
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Soft delete - Instead of deleting records, we mark them as deleted
    # This preserves data integrity and audit trails
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    # Relationship to Employee (one-to-one)
    # The back_populates creates a two-way relationship
    employee: Optional["Employee"] = Relationship(back_populates="user")


# ============================================================================
# DEPARTMENT MODEL - Organizational structure
# ============================================================================

class Department(SQLModel, table=True):
    """Departments organize employees into functional groups"""
    __tablename__ = "departments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    code: str = Field(unique=True, max_length=20)  # e.g., "ENG", "HR", "SALES"
    
    # Head of department (self-referential - points to an Employee)
    head_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    
    # Hierarchical department structure (parent department for nested orgs)
    parent_department_id: Optional[int] = Field(default=None, foreign_key="departments.id", index=True)
    
    # HR and escalation contacts
    hr_contact_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    
    # Cost center and budgeting
    cost_center_code: Optional[str] = Field(default=None, max_length=50)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    
    # Relationships
    employees: list["Employee"] = Relationship(
        back_populates="department",
        sa_relationship_kwargs={
            "foreign_keys": "[Employee.department_id]"
        }
    )


# ============================================================================
# LOCATION MODEL - Office locations
# ============================================================================

class Location(SQLModel, table=True):
    """Physical office locations"""
    __tablename__ = "locations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    city: str = Field(max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: str = Field(max_length=100)
    timezone: str = Field(default="UTC", max_length=50)  # e.g., "Asia/Kolkata"
    address: Optional[str] = Field(default=None, max_length=500)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    
    # Relationships
    employees: list["Employee"] = Relationship(back_populates="location")


# ============================================================================
# EMPLOYEE MODEL - Core HR data
# ============================================================================

class Employee(SQLModel, table=True):
    """
    Employee model - the heart of the HRMS.
    
    This contains all HR-related information about an employee.
    Notice how it's connected to User but contains different information.
    """
    __tablename__ = "employees"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Link to User account (one-to-one relationship)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    
    # Basic Information
    employee_id: str = Field(unique=True, index=True, max_length=50)  # e.g., "EMP001"
    first_name: str = Field(max_length=100)
    middle_name: Optional[str] = Field(default=None, max_length=100)
    last_name: str = Field(max_length=100)
    display_name: str = Field(max_length=200)  # Usually "FirstName LastName"
    
    # Contact Information
    email: str = Field(unique=True, index=True, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    personal_email: Optional[str] = Field(default=None, max_length=255)
    
    # Personal Details
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    marital_status: Optional[str] = Field(default=None, max_length=20)
    nationality: Optional[str] = Field(default=None, max_length=100)
    
    # Employment Details
    date_of_joining: date  # Required - when they started
    date_of_exit: Optional[date] = None  # When they left (if applicable)
    designation: str = Field(max_length=100)  # Job title
    employment_type: str = Field(default="full_time", max_length=50)  # full_time, part_time, contract
    
    # Organizational Relationships
    department_id: Optional[int] = Field(default=None, foreign_key="departments.id")
    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    manager_id: Optional[int] = Field(default=None, foreign_key="employees.id")  # Reports to
    
    # Compensation
    salary: Optional[float] = None  # Monthly salary
    currency: str = Field(default="INR", max_length=10)
    
    # Profile
    avatar: Optional[str] = Field(default=None, max_length=500)  # URL to profile picture
    bio: Optional[str] = Field(default=None, max_length=1000)
    
    # Status
    is_active: bool = Field(default=True)
    
    # ============================================================================
    # ENTERPRISE FEATURES - Enhanced organizational hierarchy and permissions
    # ============================================================================
    
    # Enhanced hierarchy (reporting_manager_id for explicit reporting vs manager_id for functional)
    reporting_manager_id: Optional[int] = Field(default=None, foreign_key="employees.id", index=True)
    is_manager: bool = Field(default=False, index=True)
    
    # Approval permissions
    can_approve_leave: bool = Field(default=False)
    can_approve_expenses: bool = Field(default=False)
    can_approve_timesheets: bool = Field(default=False)
    approval_limit_amount: Optional[float] = None  # Max expense amount they can approve
    
    # Notification preferences (JSON field)
    # Example: {"email": True, "slack": True, "sms": False, "in_app": True, 
    #           "digest_frequency": "immediate", "slack_webhook": "https://..."}
    notification_preferences: Optional[Dict[str, Any]] = Field(
        default=None, 
        sa_column=Column(JSON)
    )
    
    # Workload management
    current_workload_hours: float = Field(default=0)
    max_workload_hours: float = Field(default=40)  # Weekly capacity
    
    # Skills and expertise (for AI-powered work assignment)
    skills: Optional[str] = Field(default=None, max_length=1000)  # Comma-separated: "Python,React,SQL"
    expertise_areas: Optional[str] = Field(default=None, max_length=1000)  # "Backend,APIs,Database"
    
    # Role-based access control (Added in migration 006)
    role: str = Field(default="employee", max_length=50)  # 'employee', 'manager', 'hr', 'admin'
    team_id: Optional[int] = Field(default=None, index=True)  # Team assignment for isolation
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    
    # Relationships - These create the connections between tables
    user: User = Relationship(back_populates="employee")
    department: Optional[Department] = Relationship(
        back_populates="employees",
        sa_relationship_kwargs={
            "foreign_keys": "[Employee.department_id]"
        }
    )
    location: Optional[Location] = Relationship(back_populates="employees")
    
    # Self-referential relationships for manager hierarchy
    manager: Optional["Employee"] = Relationship(
        back_populates="direct_reports",
        sa_relationship_kwargs={
            "remote_side": "Employee.id",
            "foreign_keys": "[Employee.manager_id]"
        }
    )
    direct_reports: list["Employee"] = Relationship(
        back_populates="manager",
        sa_relationship_kwargs={
            "foreign_keys": "[Employee.manager_id]"
        }
    )
    
    # Note: chat_conversations relationship temporarily removed to avoid circular import
    # The relationship exists in database via foreign key, but not exposed as ORM relationship
    
    # Payroll relationship
    payrolls: list["Payroll"] = Relationship(back_populates="employee")


# Note: We'll define AttendanceDay, LeaveApplication, etc. in separate files
# This keeps the code organized and easier to maintain.
# The relationships from Employee to attendance/leaves are removed to avoid ambiguity
# since those tables have multiple FKs to employees. Access them via queries instead.
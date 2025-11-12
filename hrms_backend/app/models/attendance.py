"""
app/models/attendance.py and app/models/leave.py

These models handle the time tracking and leave management features.
Understanding the relationships here is key:
- An Employee has many AttendanceDay records (one per day)
- An Employee has multiple LeaveBalance records (one per leave type)
- An Employee can have many LeaveApplication records
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, time, date
import datetime as dt
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, ForeignKey
from enum import Enum

if TYPE_CHECKING:
    from .user import Employee


# ============================================================================
# ATTENDANCE MODELS
# ============================================================================

class AttendanceStatus(str, Enum):
    """Possible attendance statuses for a day"""
    PRESENT = "Present"
    ABSENT = "Absent"
    HALF_DAY = "Half Day"
    ON_LEAVE = "On Leave"
    WEEKEND = "Weekend"
    HOLIDAY = "Holiday"
    WORK_FROM_HOME = "Work From Home"


class AttendanceSource(str, Enum):
    """How the attendance was recorded"""
    WEB = "web"  # Clocked in via web interface
    MOBILE = "mobile"
    BIOMETRIC = "biometric"
    MANUAL = "manual"  # Manually entered by HR
    SYSTEM = "system"  # Auto-generated (weekends, holidays)


class AttendanceDay(SQLModel, table=True):
    """
    One record per employee per day.
    
    This is the core of attendance tracking. Each row represents
    one employee's attendance for one specific day.
    
    Why separate check-in and check-out? Because people might:
    - Check in multiple times (forgot to check out, came back)
    - Leave and return (lunch break)
    - Need corrections later
    """
    __tablename__ = "attendance_days"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Which employee and which day
    employee_id: int = Field(foreign_key="employees.id", index=True)
    date: dt.date = Field(index=True)  # The specific date
    
    # Status for the day
    status: AttendanceStatus = Field(default=AttendanceStatus.ABSENT)
    
    # Clock in/out times
    check_in: Optional[time] = None  # When they arrived
    check_out: Optional[time] = None  # When they left
    
    # Calculated fields
    work_hours: Optional[float] = None  # Total hours worked
    overtime_minutes: Optional[int] = Field(default=0)
    
    # Context
    source: AttendanceSource = Field(default=AttendanceSource.WEB)
    location_type: str = Field(default="office", max_length=50)  # office, remote, client_site
    ip_address: Optional[str] = Field(default=None, max_length=50)
    device_info: Optional[str] = Field(default=None, max_length=200)
    
    # Notes and approvals
    notes: Optional[str] = Field(default=None, max_length=500)
    is_regularized: bool = Field(default=False)  # Was this corrected after the fact?
    regularization_reason: Optional[str] = Field(default=None, max_length=500)
    approved_by_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Note: Composite unique constraint (employee_id, date) should be enforced via migrations.
    # Relationship removed due to ambiguous foreign keys (employee_id and approved_by_id both point to employees)


# ============================================================================
# LEAVE MANAGEMENT MODELS
# ============================================================================

class LeaveType(SQLModel, table=True):
    """
    Types of leave available (Casual, Sick, Annual, etc.)
    
    Why have this as a separate table? Because:
    - Different leave types have different rules
    - Companies can add/remove leave types
    - Makes it easy to query "how much casual leave is left?"
    """
    __tablename__ = "leave_types"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100)  # "Casual Leave"
    code: str = Field(unique=True, max_length=20)  # "CL"
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Leave rules
    default_days_per_year: int = Field(default=10)
    is_paid: bool = Field(default=True)
    requires_approval: bool = Field(default=True)
    can_be_carried_forward: bool = Field(default=False)
    max_consecutive_days: Optional[int] = None
    min_days_notice: int = Field(default=0)  # How many days in advance to apply
    
    # Status
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    leave_balances: list["LeaveBalance"] = Relationship(back_populates="leave_type")
    leave_applications: list["LeaveApplication"] = Relationship(back_populates="leave_type")


class LeaveBalance(SQLModel, table=True):
    """
    Tracks how much leave each employee has.
    
    One record per employee per leave type per year.
    For example: "John has 10 casual leave days for 2024"
    
    Why track opening/accrued/consumed separately?
    - Opening: What they started the year with
    - Accrued: What they earned during the year (some companies accrue monthly)
    - Consumed: What they've used
    - Balance: opening + accrued - consumed (calculated)
    """
    __tablename__ = "leave_balances"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    employee_id: int = Field(foreign_key="employees.id", index=True)
    leave_type_id: int = Field(foreign_key="leave_types.id", index=True)
    year: int = Field(index=True)  # Which calendar year
    
    # Balance tracking
    opening_balance: float = Field(default=0.0)  # Started year with this
    accrued: float = Field(default=0.0)  # Earned during year
    consumed: float = Field(default=0.0)  # Used so far
    balance: float = Field(default=0.0)  # Remaining (opening + accrued - consumed)
    
    # Pending applications not yet approved (reserved but not consumed)
    pending: float = Field(default=0.0)
    
    # Carried forward from previous year
    carried_forward: float = Field(default=0.0)
    
    # Encashed (converted to money instead of taking time off)
    encashed: float = Field(default=0.0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to leave_type only (employee relationship removed due to ambiguous FKs)
    leave_type: LeaveType = Relationship(back_populates="leave_balances")


class LeaveApplicationStatus(str, Enum):
    """Status of a leave application"""
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    WITHDRAWN = "Withdrawn"


class LeaveApplication(SQLModel, table=True):
    """
    Individual leave requests/applications.
    
    This is where employees request time off. Each application
    goes through a workflow: Pending -> Approved/Rejected
    """
    __tablename__ = "leave_applications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who and what type
    employee_id: int = Field(foreign_key="employees.id", index=True)
    leave_type_id: int = Field(foreign_key="leave_types.id", index=True)
    
    # Date range
    start_date: date
    end_date: date
    total_days: float  # Can be fractional for half days (e.g., 2.5 days)
    
    # Half day handling
    is_half_day: bool = Field(default=False)
    half_day_period: Optional[str] = Field(default=None, max_length=20)  # "first_half" or "second_half"
    
    # Reason and notes
    reason: str = Field(max_length=1000)
    contact_details: Optional[str] = Field(default=None, max_length=500)
    
    # Status and workflow
    status: LeaveApplicationStatus = Field(default=LeaveApplicationStatus.PENDING)
    applied_date: date = Field(default_factory=dt.date.today)
    
    # Approval chain
    approver_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    approved_date: Optional[datetime] = None
    approver_comments: Optional[str] = Field(default=None, max_length=1000)
    
    # HR processing
    processed_by_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    processed_date: Optional[datetime] = None
    
    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to leave_type only (employee relationship removed due to ambiguous FKs: employee_id, approver_id, processed_by_id)
    leave_type: LeaveType = Relationship(back_populates="leave_applications")


# ============================================================================
# HOLIDAY CALENDAR
# ============================================================================

class Holiday(SQLModel, table=True):
    """
    Company holidays (national holidays, office closures, etc.)
    
    These affect attendance calculations - if it's a holiday,
    people aren't expected to be present.
    """
    __tablename__ = "holidays"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)  # "Independence Day"
    date: dt.date
    year: int = Field(index=True)
    
    # Some holidays are optional (floating holidays)
    is_optional: bool = Field(default=False)
    
    # Location-specific holidays
    location_id: Optional[int] = Field(default=None, foreign_key="locations.id")
    
    # Description
    description: Optional[str] = Field(default=None, max_length=500)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
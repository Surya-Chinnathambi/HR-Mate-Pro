"""
Aggregate exports for models package.

To avoid duplicate class definitions and Pydantic type-annotation issues,
this module re-exports models from the concrete modules (user.py, attendance.py).
"""

# Re-export user/account/org models
from .user import (
    User,
    UserRole,
    UserStatus,
    Gender,
    Department,
    Location,
    Employee,
)

# Re-export attendance/leave/holiday models
from .attendance import (
    AttendanceStatus,
    AttendanceSource,
    AttendanceDay,
    LeaveType,
    LeaveBalance,
    LeaveApplicationStatus,
    LeaveApplication,
    Holiday,
)

from .extras import Payroll, Notification, NotificationPriority, Policy

# Re-export AI chat models
from .ai_chat import (
    ConversationHistory,
    AIChatSession,
    AIFunctionCall,
)

# Re-export workflow and organizational hierarchy models (ENTERPRISE FEATURES)
from .workflow import (
    ApprovalLevel,
    ApprovalStatus,
    RequestType,
    ApprovalChain,
    ApprovalRequest,
    ApprovalStep,
    ReportingRelationship,
    TaskPriority,
    TaskStatus,
    WorkAssignment,
    TaskComment,
    TaskTimeLog,
    AuditAction,
    AuditLog,
)

# Optional: simple aliases to maintain backwards compatibility with older API code
# Legacy names used by API routers
Attendance = AttendanceDay
Leave = LeaveApplication
LeaveStatus = LeaveApplicationStatus

__all__ = [
    # user/account/org
    "User",
    "UserRole",
    "UserStatus",
    "Gender",
    "Department",
    "Location",
    "Employee",
    # attendance/leave/holiday
    "AttendanceStatus",
    "AttendanceSource",
    "AttendanceDay",
    "Attendance",
    "LeaveType",
    "LeaveBalance",
    "LeaveApplicationStatus",
    "LeaveStatus",
    "LeaveApplication",
    "Leave",
    "Holiday",
    "Payroll",
    "Notification",
    "Policy",
    # workflow and organizational hierarchy (ENTERPRISE)
    "ApprovalLevel",
    "ApprovalStatus",
    "RequestType",
    "ApprovalChain",
    "ApprovalRequest",
    "ApprovalStep",
    "ReportingRelationship",
    "TaskPriority",
    "TaskStatus",
    "WorkAssignment",
    "TaskComment",
    "TaskTimeLog",
    "AuditAction",
    "AuditLog",
]
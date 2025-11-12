"""
Workflow and organizational hierarchy models for enterprise HRMS.

These models support:
- Multi-level approval chains
- Work assignment and task management
- Reporting relationships and matrix organizations
- Audit trails for compliance
"""

from typing import Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Index


# ============================================================================
# APPROVAL CHAIN MODELS
# ============================================================================

class ApprovalLevel(str, Enum):
    """Hierarchical approval levels"""
    TEAM_LEAD = "team_lead"
    MANAGER = "manager"
    DEPARTMENT_HEAD = "department_head"
    HR = "hr"
    C_LEVEL = "c_level"


class ApprovalStatus(str, Enum):
    """Status of approval at each level"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    AUTO_APPROVED = "auto_approved"


class RequestType(str, Enum):
    """Types of requests that require approval"""
    LEAVE = "leave"
    WFH = "wfh"
    EXPENSE = "expense"
    OVERTIME = "overtime"
    TIMESHEET_CORRECTION = "timesheet_correction"
    SALARY_ADVANCE = "salary_advance"
    TRANSFER = "transfer"
    RESIGNATION = "resignation"


class ApprovalChain(SQLModel, table=True):
    """
    Defines multi-level approval workflows for different request types.
    
    Example: Leave requests go through:
    1. Manager (if < 5 days)
    2. Manager + HR (if >= 5 days)
    3. Manager + HR + Department Head (if >= 10 days)
    """
    __tablename__ = "approval_chains"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # What kind of request and which department/role
    request_type: RequestType = Field(index=True)
    department_id: Optional[int] = Field(default=None, foreign_key="departments.id", index=True)
    
    # Approval level configuration
    level: int = Field(index=True)  # 1, 2, 3, etc.
    approval_role: ApprovalLevel = Field(index=True)
    approver_id: Optional[int] = Field(default=None, foreign_key="employees.id")  # Specific person or null for role-based
    
    # Conditions for this level to apply
    min_amount: Optional[float] = None  # For expense approvals
    max_amount: Optional[float] = None
    min_days: Optional[int] = None  # For leave approvals
    max_days: Optional[int] = None
    
    # Escalation settings
    escalation_hours: int = Field(default=24)  # Auto-escalate after this many hours
    reminder_hours: int = Field(default=12)  # Send reminder after this many hours
    
    # Configuration
    is_mandatory: bool = Field(default=True)  # Can this level be skipped?
    parallel_approval: bool = Field(default=False)  # Can multiple approvers at same level approve in parallel?
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    __table_args__ = (
        Index('idx_approval_chain_lookup', 'request_type', 'department_id', 'level'),
    )


class ApprovalRequest(SQLModel, table=True):
    """
    Tracks approval requests through the chain.
    
    Each request can have multiple approval steps.
    """
    __tablename__ = "approval_requests"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Link to the actual entity being approved
    entity_type: str = Field(index=True)  # "leave_application", "expense", etc.
    entity_id: int = Field(index=True)
    
    # Who requested
    requester_id: int = Field(foreign_key="employees.id", index=True)
    request_type: RequestType = Field(index=True)
    
    # Overall status
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, index=True)
    current_level: int = Field(default=1)
    
    # Request details
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    amount: Optional[float] = None  # For expense/salary requests
    days: Optional[int] = None  # For leave requests
    
    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = None
    
    # Escalation tracking
    last_reminder_sent: Optional[datetime] = None
    escalation_count: int = Field(default=0)
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_approval_entity', 'entity_type', 'entity_id'),
        Index('idx_approval_status_date', 'status', 'requested_at'),
    )


class ApprovalStep(SQLModel, table=True):
    """
    Individual approval steps within a request chain.
    """
    __tablename__ = "approval_steps"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    approval_request_id: int = Field(foreign_key="approval_requests.id", index=True)
    level: int = Field(index=True)
    
    # Who needs to approve
    approver_id: int = Field(foreign_key="employees.id", index=True)
    approval_role: ApprovalLevel
    
    # Status and timing
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, index=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    
    # Response
    comments: Optional[str] = Field(default=None, max_length=1000)
    
    # Escalation
    escalated_from_id: Optional[int] = Field(default=None, foreign_key="employees.id")  # If escalated, who was the original approver
    escalated_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_approval_step_status', 'approver_id', 'status'),
    )


# ============================================================================
# ORGANIZATIONAL HIERARCHY MODELS
# ============================================================================

class ReportingRelationship(SQLModel, table=True):
    """
    Defines reporting relationships in the organization.
    
    Supports:
    - Direct reporting (solid line)
    - Dotted line reporting (matrix organizations)
    - Temporary reporting (project-based)
    """
    __tablename__ = "reporting_relationships"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who reports to whom
    employee_id: int = Field(foreign_key="employees.id", index=True)
    manager_id: int = Field(foreign_key="employees.id", index=True)
    
    # Type of relationship
    relationship_type: str = Field(default="direct", max_length=20)  # direct, dotted, temporary
    is_primary: bool = Field(default=True)  # Primary manager vs. secondary
    
    # For matrix organizations
    context: Optional[str] = Field(default=None, max_length=200)  # "Project Apollo", "Sales Initiative"
    
    # Validity period
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None
    
    # Permissions
    can_approve_leave: bool = Field(default=True)
    can_approve_expenses: bool = Field(default=False)
    can_approve_timesheets: bool = Field(default=True)
    can_assign_work: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    __table_args__ = (
        Index('idx_reporting_employee', 'employee_id', 'is_active'),
        Index('idx_reporting_manager', 'manager_id', 'is_active'),
    )


# ============================================================================
# WORK ASSIGNMENT MODELS
# ============================================================================

class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task lifecycle status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkAssignment(SQLModel, table=True):
    """
    Task and work assignment management.
    
    Supports:
    - Manager-to-employee task assignment
    - AI-suggested task distribution
    - Workload tracking
    - Task dependencies
    """
    __tablename__ = "work_assignments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Assignment details
    title: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, max_length=2000)
    
    # Who assigned to whom
    assigner_id: int = Field(foreign_key="employees.id", index=True)
    assignee_id: int = Field(foreign_key="employees.id", index=True)
    
    # Task properties
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, index=True)
    status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, index=True)
    
    # Scheduling
    assigned_date: date = Field(default_factory=date.today, index=True)
    due_date: Optional[date] = Field(default=None, index=True)
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = Field(default=0)
    
    # Completion
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = Field(default=None, max_length=1000)
    
    # Dependencies
    depends_on_task_id: Optional[int] = Field(default=None, foreign_key="work_assignments.id")
    blocks_task_ids: Optional[str] = Field(default=None, max_length=200)  # Comma-separated IDs
    
    # Progress tracking
    progress_percentage: int = Field(default=0)
    last_status_update: Optional[datetime] = None
    
    # Context
    project_name: Optional[str] = Field(default=None, max_length=200, index=True)
    tags: Optional[str] = Field(default=None, max_length=500)  # Comma-separated tags
    
    # AI assistance
    ai_suggested: bool = Field(default=False)  # Was this suggested by AI based on workload?
    ai_confidence_score: Optional[float] = None  # 0.0 to 1.0
    
    # Delegation tracking
    delegated_from_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    delegation_reason: Optional[str] = Field(default=None, max_length=500)
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    
    __table_args__ = (
        Index('idx_work_assignment_assignee_status', 'assignee_id', 'status', 'due_date'),
        Index('idx_work_assignment_assigner', 'assigner_id', 'assigned_date'),
        Index('idx_work_assignment_project', 'project_name', 'status'),
    )


class TaskComment(SQLModel, table=True):
    """Comments and updates on work assignments"""
    __tablename__ = "task_comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    task_id: int = Field(foreign_key="work_assignments.id", index=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    
    comment: str = Field(max_length=2000)
    
    # Attachments
    attachment_url: Optional[str] = Field(default=None, max_length=500)
    
    # Mentions
    mentioned_employee_ids: Optional[str] = Field(default=None, max_length=500)  # Comma-separated
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)


class TaskTimeLog(SQLModel, table=True):
    """Time logging for work assignments"""
    __tablename__ = "task_time_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    task_id: int = Field(foreign_key="work_assignments.id", index=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    
    # Time tracking
    log_date: date = Field(default_factory=date.today, index=True)
    hours_logged: float
    
    # Description
    work_description: Optional[str] = Field(default=None, max_length=1000)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_time_log_task_date', 'task_id', 'log_date'),
    )


# ============================================================================
# AUDIT LOG MODELS
# ============================================================================

class AuditAction(str, Enum):
    """Types of auditable actions"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    ASSIGN = "assign"
    DELEGATE = "delegate"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    EXPORT_DATA = "export_data"


class AuditLog(SQLModel, table=True):
    """
    Comprehensive audit trail for compliance.
    
    Tracks all sensitive actions, approvals, data access, and policy changes.
    """
    __tablename__ = "audit_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who did what
    user_id: int = Field(foreign_key="users.id", index=True)
    employee_id: Optional[int] = Field(default=None, foreign_key="employees.id", index=True)
    action: AuditAction = Field(index=True)
    
    # What was affected
    entity_type: str = Field(index=True)  # "leave_application", "employee", "approval_request"
    entity_id: Optional[int] = None
    
    # Details
    description: str = Field(max_length=500)
    old_value: Optional[str] = Field(default=None, sa_column=Column(JSON))  # JSON snapshot of before state
    new_value: Optional[str] = Field(default=None, sa_column=Column(JSON))  # JSON snapshot of after state
    
    # Context
    ip_address: Optional[str] = Field(default=None, max_length=50)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    request_id: Optional[str] = Field(default=None, max_length=100, index=True)  # For tracing requests
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Compliance flags
    is_policy_violation: bool = Field(default=False, index=True)
    violation_reason: Optional[str] = Field(default=None, max_length=500)
    
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action', 'timestamp'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_violations', 'is_policy_violation', 'timestamp'),
    )


# ============================================================================
# EMPLOYEE ENHANCEMENTS (Added fields for existing Employee model)
# ============================================================================

# These fields should be added to the existing Employee model in user.py:
# 
# # Enhanced organizational hierarchy
# reporting_manager_id: Optional[int] = Field(default=None, foreign_key="employees.id", index=True)
# is_manager: bool = Field(default=False, index=True)
# can_approve_leave: bool = Field(default=False)
# can_approve_expenses: bool = Field(default=False)
# approval_limit_amount: Optional[float] = None  # Max amount they can approve
# 
# # Notification preferences (JSON field)
# notification_preferences: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
# # Example: {"email": True, "slack": True, "sms": False, "in_app": True, "digest_frequency": "daily"}
# 
# # Workload capacity
# current_workload_hours: float = Field(default=0)
# max_workload_hours: float = Field(default=40)  # Weekly capacity
# 
# # Skills and expertise (for AI work assignment)
# skills: Optional[str] = Field(default=None, max_length=1000)  # Comma-separated
# expertise_areas: Optional[str] = Field(default=None, max_length=1000)

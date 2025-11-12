"""Supplemental models: Payroll, Notification, Policy, GroupChatMessage.

These were originally defined inline in the models package but got removed
during refactor. Reintroducing them here keeps separation while restoring
API compatibility.
"""
from datetime import datetime, date
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from .user import Employee

class Payroll(SQLModel, table=True):
    __tablename__ = "payrolls"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    
    # Pay period
    pay_period_start: date
    pay_period_end: date
    pay_date: Optional[date] = None
    
    # Backward compatibility
    period: Optional[str] = None  # e.g., "January 2025"
    month: Optional[int] = None
    year: Optional[int] = None
    
    # Earnings components
    basic_salary: float = Field(default=0)
    hra: float = Field(default=0)  # House Rent Allowance
    special_allowance: float = Field(default=0)
    transport_allowance: float = Field(default=0)
    medical_allowance: float = Field(default=0)
    other_allowances: float = Field(default=0)
    gross_salary: float = Field(default=0)
    
    # Legacy field (for backward compatibility)
    gross_pay: Optional[float] = None
    
    # Deductions
    pf_employee: float = Field(default=0)  # Employee PF contribution
    pf_employer: float = Field(default=0)  # Employer PF contribution
    income_tax: float = Field(default=0)  # TDS
    professional_tax: float = Field(default=0)
    other_deductions: float = Field(default=0)
    total_deductions: float = Field(default=0)
    
    # Legacy field (for backward compatibility)
    deductions: Optional[float] = None
    
    # Net salary
    net_salary: float = Field(default=0)
    
    # Legacy field (for backward compatibility)
    net_pay: Optional[float] = None
    
    # Payment details
    payment_mode: str = Field(default="Bank Transfer")
    status: str = Field(default="Paid")
    payment_date: Optional[date] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    employee: Employee = Relationship(back_populates="payrolls")

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: Optional[int] = Field(foreign_key="employees.id", index=True)
    title: str
    message: str
    type: str = Field(default="info")
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM)
    is_read: bool = Field(default=False)
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

class Policy(SQLModel, table=True):
    __tablename__ = "policies"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    category: str
    content: str
    version: str = Field(default="1.0")
    is_active: bool = Field(default=True)
    effective_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GroupChatMessage(SQLModel, table=True):
    """
    Company-wide group chat messages.
    All employees can see and send messages in the main chat room.
    Uses WebSocket for real-time delivery.
    """
    __tablename__ = "group_chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Sender information
    sender_id: int = Field(foreign_key="employees.id", index=True)
    sender_name: str = Field(max_length=200)  # Denormalized for quick display
    sender_role: str = Field(max_length=50)   # employee, manager, hr, super_admin
    
    # Message content
    message: str = Field(max_length=2000)
    message_type: str = Field(default="text", max_length=20)  # text, image, file, system
    
    # Optional attachments
    attachment_url: Optional[str] = Field(default=None, max_length=500)
    attachment_type: Optional[str] = Field(default=None, max_length=50)  # image/png, application/pdf, etc.
    attachment_name: Optional[str] = Field(default=None, max_length=200)
    
    # Metadata
    is_edited: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    # Reactions (JSON array of {emoji, employee_ids[]})
    reactions: Optional[str] = Field(default=None, max_length=1000)  # JSON string
    
    # Threading (optional - for replies)
    reply_to_id: Optional[int] = Field(default=None, foreign_key="group_chat_messages.id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatReadReceipt(SQLModel, table=True):
    """
    Tracks which messages each employee has read.
    Used for unread count badges.
    """
    __tablename__ = "chat_read_receipts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    last_read_message_id: int = Field(foreign_key="group_chat_messages.id")
    last_read_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Composite unique constraint: one record per employee
    # Handled at application level


__all__ = [
    "Payroll",
    "NotificationPriority",
    "Notification",
    "Policy",
    "GroupChatMessage",
    "ChatReadReceipt",
]
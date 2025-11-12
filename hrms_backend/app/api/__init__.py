# API Router Exports
# Import all routers here for easy access in main.py

from app.api import (
    auth,
    employees,
    attendance,
    leaves,
    payroll,
    realtime,
    ai,
    policies,
    group_chat
)

__all__ = [
    "auth",
    "employees",
    "attendance",
    "leaves",
    "payroll",
    "realtime",
    "ai",
    "policies",
    "group_chat"
]
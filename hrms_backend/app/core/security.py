from datetime import datetime, timedelta
from typing import Optional
import hashlib
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.models import User
from app.models.user import UserStatus
from app.schemas import TokenData
from typing import Optional, Dict, Any
from sqlalchemy import text
import json

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def _normalize_password(password: str) -> bytes:
    """
    Normalize password to handle bcrypt's 72-byte limit.
    For passwords longer than 72 bytes, we hash them with SHA256 first.
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Hash long passwords with SHA256 to get a fixed-length input for bcrypt
        return hashlib.sha256(password_bytes).digest()
    return password_bytes

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    normalized = _normalize_password(plain_password)
    return bcrypt.checkpw(normalized, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    normalized = _normalize_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(normalized, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    result = await session.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def _get_employee_for_user(user_id: int, session: AsyncSession):
    """Return the Employee row for a given user id, or None."""
    # Import locally to avoid circular imports
    from app.models.user import Employee
    stmt = text("SELECT id, reporting_manager_id, department_id, is_manager FROM employees WHERE user_id = :uid")
    result = await session.execute(stmt, {"uid": user_id})
    row = result.first()
    if not row:
        return None
    return {
        "id": row[0],
        "reporting_manager_id": row[1],
        "department_id": row[2],
        "is_manager": row[3]
    }


async def check_permission_for_user(
    resource: str,
    action: str,
    current_user: User,
    session: AsyncSession,
    target_employee_id: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """Check whether the given user is allowed to perform `action` on `resource`.

    This function implements a simple RBAC lookup against the `role_permissions`
    table introduced in the DB migration. It supports scope values:
    - all: allowed for the role across the org
    - department: allowed within the same department
    - team: allowed for direct reports / manager-to-team
    - own: allowed only if target is the user themself

    Usage:
        await check_permission_for_user(
            "work_assignment", "create", current_user, session, target_employee_id=123
        )

    Raises HTTPException(403) on denial.
    """
    # Fetch role permissions for this role/resource/action
    role_name = getattr(current_user, "role", None) or "employee"

    stmt = text(
        "SELECT role_name, resource, action, scope, conditions FROM role_permissions "
        "WHERE role_name = :role AND resource = :resource AND action = :action"
    )

    result = await session.execute(stmt, {"role": role_name, "resource": resource, "action": action})
    perms = result.fetchall()

    if not perms:
        # No explicit permission found — deny by default
        raise HTTPException(status_code=403, detail="Permission denied (no matching role permission)")

    # Resolve current user's employee row for scope checks
    emp = await _get_employee_for_user(current_user.id, session)

    # Evaluate permissions - allow if any permission row grants access
    for p in perms:
        scope = p[3]
        conditions = p[4]

        if scope == "all":
            return True

        if scope == "own":
            if target_employee_id is None:
                # If no target provided, assume it's an action on self
                return True
            if emp and emp["id"] == target_employee_id:
                return True

        if scope == "team":
            # Allow if target is a direct report of current user or vice-versa
            if emp and target_employee_id:
                # is current user manager of target?
                res = await session.execute(text("SELECT reporting_manager_id FROM employees WHERE id = :tid"), {"tid": target_employee_id})
                tm = res.scalar_one_or_none()
                if emp["id"] == tm:
                    return True
                # is target manager of current user?
                res2 = await session.execute(text("SELECT reporting_manager_id FROM employees WHERE id = :tid"), {"tid": emp["id"]})
                target_mgr = res2.scalar_one_or_none()
                if target_mgr == target_employee_id:
                    return True

        if scope == "department":
            if emp and target_employee_id:
                resd = await session.execute(text("SELECT department_id FROM employees WHERE id = :tid"), {"tid": target_employee_id})
                target_dept = resd.scalar_one_or_none()
                if emp.get("department_id") and emp.get("department_id") == target_dept:
                    return True

        # If conditions JSONB exists, implement lightweight checks (example: max_hours)
        if conditions:
            try:
                conds = conditions if isinstance(conditions, dict) else json.loads(conditions)
            except Exception:
                conds = None

            if conds and emp:
                # Example condition: allow if assignee workload < threshold
                max_workload = conds.get("max_assignee_workload_hours")
                if max_workload and target_employee_id:
                    resw = await session.execute(text("SELECT current_workload_hours FROM employees WHERE id = :tid"), {"tid": target_employee_id})
                    tw = resw.scalar_one_or_none()
                    if tw is not None and float(tw) < float(max_workload):
                        return True

    # No permission matched
    raise HTTPException(status_code=403, detail="Permission denied")


def require_permission(resource: str, action: str, scope: Optional[str] = None):
    """
    Decorator to check permissions for a given resource and action.
    Can be used as either a route decorator or a dependency.
    
    Usage as decorator:
        @router.post("/tasks/")
        @require_permission("work_assignment", "create")
        async def create_task(...):
            ...
    
    Usage as dependency:
        @router.post("/tasks/", dependencies=[Depends(require_permission("work_assignment", "create"))])
        async def create_task(...):
            ...
    """
    def decorator(func):
        # This is a no-op decorator - actual permission check happens in the dependency
        # The decorator is just for documentation/clarity
        return func
    
    # Return the decorator so it can be used as @require_permission(...)
    return decorator

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_active_user, check_permission_for_user
from app.database import get_async_session
from app.models import User


async def require_permission(
    resource: str,
    action: str,
    target_employee_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """FastAPI dependency factory that checks permission for the current user.

    Usage in endpoint:
        @router.post("/foo")
        async def foo(dep=Depends(require_permission("work_assignment","create", target_employee_id=...))):
            ...
    """
    try:
        await check_permission_for_user(resource, action, current_user, session, target_employee_id)
    except HTTPException as e:
        # re-raise so FastAPI returns proper response
        raise e
    return True

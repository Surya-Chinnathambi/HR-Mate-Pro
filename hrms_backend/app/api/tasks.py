"""
Tasks API
Alias/wrapper for work assignments with simpler interface
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_async_session
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to_employee_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[str] = None


@router.get("/")
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get tasks (wrapper for work assignments)
    """
    try:
        # Get employee_id
        emp_query = text("SELECT id FROM employees WHERE user_id = :user_id")
        emp_result = await db.execute(emp_query, {"user_id": current_user.id})
        employee = emp_result.fetchone()
        
        if not employee:
            return {"tasks": [], "total": 0}
        
        employee_id = employee[0]
        
        # Build query for work_assignments table
        conditions = [
            "(assigned_to_employee_id = :employee_id OR created_by_employee_id = :employee_id)"
        ]
        params = {"employee_id": employee_id, "skip": skip, "limit": limit}
        
        if status:
            conditions.append("status = :status")
            params["status"] = status
        
        if priority:
            conditions.append("priority = :priority")
            params["priority"] = priority
        
        where_clause = " AND ".join(conditions)
        
        # Get tasks from work_assignments table
        query = text(f"""
            SELECT 
                id, title, description, priority, status, due_date,
                assigned_to_employee_id, created_by_employee_id, created_at, updated_at
            FROM work_assignments
            WHERE {where_clause}
            ORDER BY created_at DESC
            OFFSET :skip LIMIT :limit
        """)
        
        result = await db.execute(query, params)
        tasks = result.fetchall()
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) FROM work_assignments WHERE {where_clause}
        """)
        count_result = await db.execute(count_query, {k: v for k, v in params.items() if k not in ['skip', 'limit']})
        total = count_result.scalar()
        
        return {
            "tasks": [
                {
                    "id": t[0],
                    "title": t[1],
                    "description": t[2],
                    "priority": t[3],
                    "status": t[4],
                    "due_date": t[5].isoformat() if t[5] else None,
                    "assigned_to_employee_id": t[6],
                    "created_by_employee_id": t[7],
                    "created_at": t[8].isoformat() if t[8] else None,
                    "updated_at": t[9].isoformat() if t[9] else None
                }
                for t in tasks
            ],
            "total": total
        }
        
    except Exception as e:
        # Return empty tasks if table doesn't exist or other error
        print(f"Tasks fetch error: {str(e)}")
        return {
            "tasks": [],
            "total": 0,
            "message": "Tasks feature coming soon"
        }


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific task"""
    try:
        query = text("""
            SELECT 
                id, title, description, priority, status, due_date,
                assigned_to_employee_id, created_by_employee_id, created_at, updated_at
            FROM work_assignments
            WHERE id = :task_id
        """)
        
        result = await db.execute(query, {"task_id": task_id})
        task = result.fetchone()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return {
            "id": task[0],
            "title": task[1],
            "description": task[2],
            "priority": task[3],
            "status": task[4],
            "due_date": task[5].isoformat() if task[5] else None,
            "assigned_to_employee_id": task[6],
            "created_by_employee_id": task[7],
            "created_at": task[8].isoformat() if task[8] else None,
            "updated_at": task[9].isoformat() if task[9] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task: {str(e)}"
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new task"""
    try:
        # Get employee_id
        emp_query = text("SELECT id FROM employees WHERE user_id = :user_id")
        emp_result = await db.execute(emp_query, {"user_id": current_user.id})
        employee = emp_result.fetchone()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee profile not found"
            )
        
        employee_id = employee[0]
        
        # Insert task
        query = text("""
            INSERT INTO work_assignments 
            (title, description, assigned_to_employee_id, created_by_employee_id, 
             priority, status, due_date, created_at, updated_at)
            VALUES 
            (:title, :description, :assigned_to, :created_by, 
             :priority, 'pending', :due_date, :created_at, :updated_at)
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "title": task.title,
            "description": task.description,
            "assigned_to": task.assigned_to_employee_id or employee_id,
            "created_by": employee_id,
            "priority": task.priority,
            "due_date": task.due_date,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        await db.commit()
        
        task_id = result.scalar()
        
        return {
            "id": task_id,
            "message": "Task created successfully"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Update a task"""
    try:
        query = text("""
            UPDATE work_assignments
            SET title = :title,
                description = :description,
                priority = :priority,
                due_date = :due_date,
                updated_at = :updated_at
            WHERE id = :task_id
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "task_id": task_id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "due_date": task.due_date,
            "updated_at": datetime.utcnow()
        })
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return {"message": "Task updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )


@router.post("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    comments: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Update task status"""
    try:
        query = text("""
            UPDATE work_assignments
            SET status = :status, updated_at = :updated_at
            WHERE id = :task_id
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "task_id": task_id,
            "status": status,
            "updated_at": datetime.utcnow()
        })
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return {"message": f"Task status updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task status: {str(e)}"
        )


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a task"""
    try:
        query = text("""
            DELETE FROM work_assignments
            WHERE id = :task_id
            RETURNING id
        """)
        
        result = await db.execute(query, {"task_id": task_id})
        await db.commit()
        
        if not result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return {"message": "Task deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )

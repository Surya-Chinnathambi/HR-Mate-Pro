"""
Work Assignment & Task Management Automation Service
Provides automated task assignment, tracking, and workload management
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from decimal import Decimal


class TaskAutomationService:
    """
    Automated task management service
    - Task assignment with workload checking
    - Auto-suggest team members by capacity
    - Task status updates and tracking
    - Time logging
    - Workload balancing
    """
    
    @staticmethod
    async def get_my_tasks(
        db: AsyncSession,
        employee_id: int,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tasks assigned to employee"""
        from app.models.workflow import WorkAssignment, TaskStatus
        
        # Build query
        conditions = [WorkAssignment.assigned_to_id == employee_id]
        if status:
            conditions.append(WorkAssignment.status == status)
        
        stmt = select(WorkAssignment).where(and_(*conditions)).order_by(WorkAssignment.due_date)
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        
        # Categorize tasks
        overdue = []
        due_soon = []
        in_progress = []
        pending = []
        
        today = date.today()
        
        for task in tasks:
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else 0
            }
            
            if task.due_date and task.due_date < today and task.status != TaskStatus.COMPLETED:
                overdue.append(task_data)
            elif task.due_date and (task.due_date - today).days <= 3:
                due_soon.append(task_data)
            elif task.status == TaskStatus.IN_PROGRESS:
                in_progress.append(task_data)
            else:
                pending.append(task_data)
        
        return {
            "success": True,
            "total_tasks": len(tasks),
            "overdue": overdue,
            "due_soon": due_soon,
            "in_progress": in_progress,
            "pending": pending,
            "summary": {
                "overdue_count": len(overdue),
                "due_soon_count": len(due_soon),
                "in_progress_count": len(in_progress),
                "pending_count": len(pending)
            }
        }
    
    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: int,
        employee_id: int,
        new_status: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update task status"""
        from app.models.workflow import WorkAssignment, TaskStatus, TaskComment
        
        # Get task
        stmt = select(WorkAssignment).where(WorkAssignment.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return {
                "success": False,
                "error": "task_not_found",
                "message": "Task not found"
            }
        
        # Verify assignment
        if task.assigned_to_id != employee_id:
            return {
                "success": False,
                "error": "unauthorized",
                "message": "You are not assigned to this task"
            }
        
        # Update status
        old_status = task.status
        try:
            task.status = TaskStatus(new_status.lower())
        except ValueError:
            return {
                "success": False,
                "error": "invalid_status",
                "message": f"Invalid status: {new_status}. Valid: todo, in_progress, completed, blocked"
            }
        
        task.updated_at = datetime.utcnow()
        
        # Add comment if provided
        if comment:
            task_comment = TaskComment(
                task_id=task_id,
                employee_id=employee_id,
                comment=comment,
                created_at=datetime.utcnow()
            )
            db.add(task_comment)
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Task status updated from {old_status} to {new_status}",
            "task_id": task_id,
            "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
            "new_status": new_status,
            "comment_added": comment is not None
        }
    
    @staticmethod
    async def log_time(
        db: AsyncSession,
        task_id: int,
        employee_id: int,
        hours: float,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log time spent on task"""
        from app.models.workflow import WorkAssignment, TaskTimeLog
        
        # Get task
        stmt = select(WorkAssignment).where(WorkAssignment.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return {
                "success": False,
                "error": "task_not_found",
                "message": "Task not found"
            }
        
        # Create time log
        time_log = TaskTimeLog(
            task_id=task_id,
            employee_id=employee_id,
            hours_spent=hours,
            description=description,
            logged_at=datetime.utcnow()
        )
        
        db.add(time_log)
        await db.commit()
        
        # Calculate total time spent
        stmt = select(func.sum(TaskTimeLog.hours_spent)).where(TaskTimeLog.task_id == task_id)
        result = await db.execute(stmt)
        total_hours = result.scalar() or 0
        
        return {
            "success": True,
            "message": f"Logged {hours} hours on task",
            "task_id": task_id,
            "hours_logged": hours,
            "total_hours_spent": float(total_hours),
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours else 0,
            "remaining_hours": (float(task.estimated_hours) - float(total_hours)) if task.estimated_hours else None
        }
    
    @staticmethod
    async def assign_task(
        db: AsyncSession,
        manager_id: int,
        title: str,
        description: str,
        assignee_id: int,
        due_date: date,
        priority: str = "medium",
        estimated_hours: Optional[float] = None
    ) -> Dict[str, Any]:
        """Assign task to team member (manager function)

        Note: uses `assigner_id` / `assignee_id` field names consistent with WorkAssignment model.
        """
        from app.models import Employee
        from app.models.workflow import WorkAssignment, TaskPriority, TaskStatus
        
        # Verify manager permission
        stmt = select(Employee).where(Employee.id == manager_id)
        result = await db.execute(stmt)
        manager = result.scalar_one_or_none()
        
        if not manager or not manager.is_manager:
            return {
                "success": False,
                "error": "unauthorized",
                "message": "Only managers can assign tasks"
            }
        
        # Check if assignee exists and reports to manager
        stmt = select(Employee).where(Employee.id == assignee_id)
        result = await db.execute(stmt)
        assignee = result.scalar_one_or_none()

        if not assignee:
            return {
                "success": False,
                "error": "assignee_not_found",
                "message": "Assignee not found"
            }
        
        # Create task
        try:
            task = WorkAssignment(
                title=title,
                description=description,
                assigner_id=manager_id,
                assignee_id=assignee_id,
                status=TaskStatus.NOT_STARTED,
                priority=TaskPriority(priority.lower()),
                due_date=due_date,
                estimated_hours=estimated_hours,
                assigned_date=date.today(),
                created_at=datetime.utcnow()
            )
        except ValueError:
            return {
                "success": False,
                "error": "invalid_priority",
                "message": f"Invalid priority: {priority}. Valid: low, medium, high, critical"
            }
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        return {
            "success": True,
            "message": f"Task assigned to {assignee.first_name} {assignee.last_name}",
            "task_id": task.id,
            "assignee": {
                "id": assignee.id,
                "name": f"{assignee.first_name} {assignee.last_name}"
            },
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority
        }
    
    @staticmethod
    async def get_team_workload(
        db: AsyncSession,
        manager_id: int
    ) -> Dict[str, Any]:
        """Get workload distribution across team"""
        from app.models import Employee
        from app.models.workflow import WorkAssignment, TaskStatus
        
        # Get team members
        stmt = select(Employee).where(Employee.manager_id == manager_id)
        result = await db.execute(stmt)
        team_members = result.scalars().all()
        
        workload_data = []
        
        for member in team_members:
            # Count tasks
            stmt = select(func.count(WorkAssignment.id)).where(
                and_(
                    WorkAssignment.assigned_to_id == member.id,
                    WorkAssignment.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
                )
            )
            result = await db.execute(stmt)
            active_tasks = result.scalar() or 0
            
            # Sum estimated hours
            stmt = select(func.sum(WorkAssignment.estimated_hours)).where(
                and_(
                    WorkAssignment.assigned_to_id == member.id,
                    WorkAssignment.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
                )
            )
            result = await db.execute(stmt)
            total_hours = result.scalar() or 0
            
            workload_data.append({
                "employee_id": member.id,
                "name": f"{member.first_name} {member.last_name}",
                "active_tasks": active_tasks,
                "estimated_hours": float(total_hours),
                "capacity_used_percent": round((float(total_hours) / member.max_workload_hours * 100), 1) if member.max_workload_hours else 0,
                "available_hours": member.max_workload_hours - float(total_hours) if member.max_workload_hours else 0
            })
        
        # Sort by workload
        workload_data.sort(key=lambda x: x["capacity_used_percent"], reverse=True)
        
        return {
            "success": True,
            "team_size": len(team_members),
            "team_workload": workload_data,
            "summary": {
                "total_active_tasks": sum(m["active_tasks"] for m in workload_data),
                "total_estimated_hours": sum(m["estimated_hours"] for m in workload_data),
                "most_loaded": workload_data[0]["name"] if workload_data else None,
                "least_loaded": workload_data[-1]["name"] if workload_data else None
            }
        }

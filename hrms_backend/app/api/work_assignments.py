"""
Work assignment and task management API endpoints.

Provides:
- Create and assign tasks
- Update task status and progress
- Task delegation
- Workload analytics
- Time logging
- Task comments
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.database import get_session
from app.core.security import get_current_user
from app.models import (
    User, Employee, WorkAssignment, TaskStatus, TaskPriority,
    TaskComment, TaskTimeLog, AuditLog, AuditAction
)
from app.services.notification_service import NotificationService, NotificationChannel
from app.services.task_automation import TaskAutomationService

router = APIRouter(prefix="/work-assignments", tags=["work-assignments"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class WorkAssignmentCreate(BaseModel):
    """Schema for creating a new work assignment"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    assignee_id: int
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    project_name: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated
    depends_on_task_id: Optional[int] = None


class WorkAssignmentUpdate(BaseModel):
    """Schema for updating a work assignment"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    completion_notes: Optional[str] = None


class TaskCommentCreate(BaseModel):
    """Schema for adding a comment to a task"""
    comment: str = Field(..., min_length=1, max_length=2000)
    mentioned_employee_ids: Optional[List[int]] = None


class TaskTimeLogCreate(BaseModel):
    """Schema for logging time on a task"""
    hours_logged: float = Field(..., gt=0)
    work_description: Optional[str] = None
    log_date: date = Field(default_factory=date.today)


class WorkAssignmentResponse(BaseModel):
    """Response schema for work assignment"""
    id: int
    title: str
    description: Optional[str]
    assigner_id: int
    assigner_name: str
    assignee_id: int
    assignee_name: str
    priority: TaskPriority
    status: TaskStatus
    assigned_date: date
    due_date: Optional[date]
    estimated_hours: Optional[float]
    actual_hours: float
    progress_percentage: int
    project_name: Optional[str]
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_current_employee(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Employee:
    """Get current user's employee record"""
    stmt = select(Employee).where(Employee.user_id == current_user.id)
    result = await session.execute(stmt)
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee record not found"
        )
    
    return employee


async def check_task_access(
    task_id: int,
    employee: Employee,
    session: Session,
    require_owner: bool = False
) -> WorkAssignment:
    """Check if employee has access to task"""
    stmt = select(WorkAssignment).where(WorkAssignment.id == task_id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check access rights
    has_access = (
        task.assignee_id == employee.id or
        task.assigner_id == employee.id or
        employee.is_manager
    )
    
    if require_owner and task.assigner_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task assigner can perform this action"
        )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )
    
    return task


# ============================================================================
# TASK CRUD ENDPOINTS
# ============================================================================

@router.post("/", response_model=WorkAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_work_assignment(
    data: WorkAssignmentCreate,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Create a new work assignment.
    
    AI-powered workload suggestions are provided via the AI chatbot interface.
    """
    # Verify assignee exists
    assignee = await session.get(Employee, data.assignee_id)
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignee with ID {data.assignee_id} not found"
        )
    
    # Check if assigner has permission (manager or can assign work)
    if not employee.is_manager and employee.id != data.assignee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to assign work to others"
        )
    
    # Create work assignment
    task = WorkAssignment(
        title=data.title,
        description=data.description,
        assigner_id=employee.id,
        assignee_id=data.assignee_id,
        priority=data.priority,
        status=TaskStatus.NOT_STARTED,
        due_date=data.due_date,
        estimated_hours=data.estimated_hours,
        project_name=data.project_name,
        tags=data.tags,
        depends_on_task_id=data.depends_on_task_id,
        assigned_date=date.today()
    )
    
    session.add(task)
    await session.commit()
    await session.refresh(task)
    
    # Update assignee's workload
    if data.estimated_hours:
        assignee.current_workload_hours += data.estimated_hours
        await session.commit()
    
    # Send notification to assignee
    notification_service = NotificationService(session)
    await notification_service.send_notification(
        employee_id=data.assignee_id,
        title=f"New Task Assigned: {task.title}",
        message=f"{employee.display_name} has assigned you a new task.",
        notification_type="task_assigned",
        entity_type="work_assignment",
        entity_id=task.id,
        channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
    )
    
    # Audit log
    audit = AuditLog(
        user_id=employee.user_id,
        employee_id=employee.id,
        action=AuditAction.ASSIGN,
        entity_type="work_assignment",
        entity_id=task.id,
        description=f"Assigned task '{task.title}' to {assignee.display_name}"
    )
    session.add(audit)
    await session.commit()
    
    # Build response
    response = WorkAssignmentResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        assigner_id=employee.id,
        assigner_name=employee.display_name,
        assignee_id=assignee.id,
        assignee_name=assignee.display_name,
        priority=task.priority,
        status=task.status,
        assigned_date=task.assigned_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours or 0,
        progress_percentage=task.progress_percentage,
        project_name=task.project_name,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at
    )
    
    return response


@router.get("/", response_model=List[WorkAssignmentResponse])
async def list_work_assignments(
    assignee_id: Optional[int] = Query(None, description="Filter by assignee"),
    assigner_id: Optional[int] = Query(None, description="Filter by assigner"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    project_name: Optional[str] = Query(None, description="Filter by project"),
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    List work assignments with filters.
    
    Employees see tasks assigned to them or by them.
    Managers see all tasks for their team.
    """
    # Build query
    conditions = []
    
    # Permission-based filtering
    if not employee.is_manager:
        # Regular employees only see their own tasks
        conditions.append(
            or_(
                WorkAssignment.assignee_id == employee.id,
                WorkAssignment.assigner_id == employee.id
            )
        )
    
    # Apply filters
    if assignee_id:
        conditions.append(WorkAssignment.assignee_id == assignee_id)
    if assigner_id:
        conditions.append(WorkAssignment.assigner_id == assigner_id)
    if status:
        conditions.append(WorkAssignment.status == status)
    if priority:
        conditions.append(WorkAssignment.priority == priority)
    if project_name:
        conditions.append(WorkAssignment.project_name.ilike(f"%{project_name}%"))
    
    conditions.append(WorkAssignment.is_deleted == False)
    
    stmt = (
        select(WorkAssignment)
        .where(and_(*conditions))
        .order_by(WorkAssignment.due_date.asc().nullslast(), WorkAssignment.priority.desc())
    )
    
    result = await session.execute(stmt)
    tasks = result.scalars().all()
    
    # Build responses with employee names
    responses = []
    for task in tasks:
        assigner = await session.get(Employee, task.assigner_id)
        assignee = await session.get(Employee, task.assignee_id)
        
        responses.append(WorkAssignmentResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            assigner_id=task.assigner_id,
            assigner_name=assigner.display_name if assigner else "Unknown",
            assignee_id=task.assignee_id,
            assignee_name=assignee.display_name if assignee else "Unknown",
            priority=task.priority,
            status=task.status,
            assigned_date=task.assigned_date,
            due_date=task.due_date,
            estimated_hours=task.estimated_hours,
            actual_hours=task.actual_hours or 0,
            progress_percentage=task.progress_percentage,
            project_name=task.project_name,
            tags=task.tags,
            created_at=task.created_at,
            updated_at=task.updated_at
        ))
    
    return responses


@router.get("/{task_id}", response_model=WorkAssignmentResponse)
async def get_work_assignment(
    task_id: int,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Get detailed information about a specific task"""
    task = await check_task_access(task_id, employee, session)
    
    assigner = await session.get(Employee, task.assigner_id)
    assignee = await session.get(Employee, task.assignee_id)
    
    return WorkAssignmentResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        assigner_id=task.assigner_id,
        assigner_name=assigner.display_name if assigner else "Unknown",
        assignee_id=task.assignee_id,
        assignee_name=assignee.display_name if assignee else "Unknown",
        priority=task.priority,
        status=task.status,
        assigned_date=task.assigned_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours or 0,
        progress_percentage=task.progress_percentage,
        project_name=task.project_name,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.put("/{task_id}", response_model=WorkAssignmentResponse)
async def update_work_assignment(
    task_id: int,
    data: WorkAssignmentUpdate,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Update task details, status, or progress"""
    task = await check_task_access(task_id, employee, session)
    
    # Track what changed for notifications
    status_changed = False
    old_status = task.status
    
    # Update fields
    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    if data.status is not None:
        status_changed = (data.status != old_status)
        task.status = data.status
        task.last_status_update = datetime.utcnow()
        
        if data.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
            task.progress_percentage = 100
    if data.due_date is not None:
        task.due_date = data.due_date
    if data.estimated_hours is not None:
        task.estimated_hours = data.estimated_hours
    if data.progress_percentage is not None:
        task.progress_percentage = data.progress_percentage
    if data.completion_notes is not None:
        task.completion_notes = data.completion_notes
    
    task.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(task)
    
    # Send notification if status changed
    if status_changed:
        notification_service = NotificationService(session)
        
        # Notify assigner
        await notification_service.send_notification(
            employee_id=task.assigner_id,
            title=f"Task Status Updated: {task.title}",
            message=f"Status changed from {old_status.value} to {task.status.value}",
            notification_type="task_status_updated",
            entity_type="work_assignment",
            entity_id=task.id,
            channels=[NotificationChannel.IN_APP]
        )
    
    assigner = await session.get(Employee, task.assigner_id)
    assignee = await session.get(Employee, task.assignee_id)
    
    return WorkAssignmentResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        assigner_id=task.assigner_id,
        assigner_name=assigner.display_name if assigner else "Unknown",
        assignee_id=task.assignee_id,
        assignee_name=assignee.display_name if assignee else "Unknown",
        priority=task.priority,
        status=task.status,
        assigned_date=task.assigned_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours or 0,
        progress_percentage=task.progress_percentage,
        project_name=task.project_name,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.post("/{task_id}/delegate")
async def delegate_task(
    task_id: int,
    new_assignee_id: int,
    reason: Optional[str] = None,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Delegate a task to another employee"""
    task = await check_task_access(task_id, employee, session)
    
    # Only assignee can delegate
    if task.assignee_id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the current assignee can delegate this task"
        )
    
    # Verify new assignee exists
    new_assignee = await session.get(Employee, new_assignee_id)
    if not new_assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {new_assignee_id} not found"
        )
    
    old_assignee_id = task.assignee_id
    
    # Update task
    task.assignee_id = new_assignee_id
    task.delegated_from_id = employee.id
    task.delegation_reason = reason
    task.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Update workloads
    if task.estimated_hours:
        employee.current_workload_hours = max(0, employee.current_workload_hours - task.estimated_hours)
        new_assignee.current_workload_hours += task.estimated_hours
        await session.commit()
    
    # Notifications
    notification_service = NotificationService(session)
    
    # Notify new assignee
    await notification_service.send_notification(
        employee_id=new_assignee_id,
        title=f"Task Delegated to You: {task.title}",
        message=f"{employee.display_name} has delegated a task to you.",
        notification_type="task_delegated",
        entity_type="work_assignment",
        entity_id=task.id,
        channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
    )
    
    # Notify original assigner
    await notification_service.send_notification(
        employee_id=task.assigner_id,
        title=f"Task Delegated: {task.title}",
        message=f"{employee.display_name} delegated this task to {new_assignee.display_name}.",
        notification_type="task_delegated",
        entity_type="work_assignment",
        entity_id=task.id,
        channels=[NotificationChannel.IN_APP]
    )
    
    # Audit log
    audit = AuditLog(
        user_id=employee.user_id,
        employee_id=employee.id,
        action=AuditAction.DELEGATE,
        entity_type="work_assignment",
        entity_id=task.id,
        description=f"Delegated task to {new_assignee.display_name}"
    )
    session.add(audit)
    await session.commit()
    
    return {"success": True, "message": "Task delegated successfully"}


# ============================================================================
# TASK COMMENTS
# ============================================================================

@router.post("/{task_id}/comments")
async def add_task_comment(
    task_id: int,
    data: TaskCommentCreate,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Add a comment to a task"""
    task = await check_task_access(task_id, employee, session)
    
    comment = TaskComment(
        task_id=task_id,
        employee_id=employee.id,
        comment=data.comment,
        mentioned_employee_ids=",".join(map(str, data.mentioned_employee_ids)) if data.mentioned_employee_ids else None
    )
    
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    
    # Send notifications to mentioned employees
    if data.mentioned_employee_ids:
        notification_service = NotificationService(session)
        for mentioned_id in data.mentioned_employee_ids:
            await notification_service.send_notification(
                employee_id=mentioned_id,
                title=f"You were mentioned in task: {task.title}",
                message=f"{employee.display_name} mentioned you in a comment.",
                notification_type="task_mention",
                entity_type="work_assignment",
                entity_id=task_id,
                channels=[NotificationChannel.IN_APP]
            )
    
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "employee_id": comment.employee_id,
        "employee_name": employee.display_name,
        "comment": comment.comment,
        "created_at": comment.created_at
    }


@router.get("/{task_id}/comments")
async def get_task_comments(
    task_id: int,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Get all comments for a task"""
    task = await check_task_access(task_id, employee, session)
    
    stmt = (
        select(TaskComment)
        .where(TaskComment.task_id == task_id)
        .where(TaskComment.is_deleted == False)
        .order_by(TaskComment.created_at.asc())
    )
    
    result = await session.execute(stmt)
    comments = result.scalars().all()
    
    responses = []
    for comment in comments:
        commenter = await session.get(Employee, comment.employee_id)
        responses.append({
            "id": comment.id,
            "task_id": comment.task_id,
            "employee_id": comment.employee_id,
            "employee_name": commenter.display_name if commenter else "Unknown",
            "comment": comment.comment,
            "created_at": comment.created_at
        })
    
    return responses


# ============================================================================
# TIME LOGGING
# ============================================================================

@router.post("/{task_id}/time-logs")
async def log_time_on_task(
    task_id: int,
    data: TaskTimeLogCreate,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Log time spent on a task"""
    task = await check_task_access(task_id, employee, session)
    
    time_log = TaskTimeLog(
        task_id=task_id,
        employee_id=employee.id,
        hours_logged=data.hours_logged,
        work_description=data.work_description,
        log_date=data.log_date
    )
    
    session.add(time_log)
    
    # Update task actual hours
    task.actual_hours = (task.actual_hours or 0) + data.hours_logged
    task.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(time_log)
    
    return {
        "id": time_log.id,
        "task_id": time_log.task_id,
        "hours_logged": time_log.hours_logged,
        "log_date": time_log.log_date,
        "work_description": time_log.work_description
    }


@router.get("/{task_id}/time-logs")
async def get_task_time_logs(
    task_id: int,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Get all time logs for a task"""
    task = await check_task_access(task_id, employee, session)
    
    stmt = (
        select(TaskTimeLog)
        .where(TaskTimeLog.task_id == task_id)
        .order_by(TaskTimeLog.log_date.desc())
    )
    
    result = await session.execute(stmt)
    logs = result.scalars().all()
    
    responses = []
    for log in logs:
        logger_emp = await session.get(Employee, log.employee_id)
        responses.append({
            "id": log.id,
            "task_id": log.task_id,
            "employee_id": log.employee_id,
            "employee_name": logger_emp.display_name if logger_emp else "Unknown",
            "hours_logged": log.hours_logged,
            "log_date": log.log_date,
            "work_description": log.work_description,
            "created_at": log.created_at
        })
    
    return responses


# ============================================================================
# WORKLOAD ANALYTICS
# ============================================================================

@router.get("/analytics/workload")
async def get_workload_analytics(
    employee_id: Optional[int] = Query(None, description="Specific employee"),
    team: bool = Query(False, description="Get team workload"),
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """Get workload analytics for an employee or team"""
    
    if employee_id:
        # Get specific employee's workload
        target_employee = await session.get(Employee, employee_id)
        if not target_employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        stmt = (
            select(WorkAssignment)
            .where(WorkAssignment.assignee_id == employee_id)
            .where(WorkAssignment.is_deleted == False)
            .where(WorkAssignment.status.in_([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]))
        )
        
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        total_estimated_hours = sum(t.estimated_hours or 0 for t in tasks)
        total_tasks = len(tasks)
        
        return {
            "employee_id": employee_id,
            "employee_name": target_employee.display_name,
            "current_workload_hours": target_employee.current_workload_hours,
            "max_workload_hours": target_employee.max_workload_hours,
            "utilization_percentage": round((target_employee.current_workload_hours / target_employee.max_workload_hours) * 100, 2) if target_employee.max_workload_hours > 0 else 0,
            "active_tasks": total_tasks,
            "total_estimated_hours": total_estimated_hours
        }
    
    elif team and employee.is_manager:
        # Get team workload (all direct reports)
        stmt = select(Employee).where(Employee.manager_id == employee.id).where(Employee.is_active == True)
        result = await session.execute(stmt)
        team_members = result.scalars().all()
        
        team_workload = []
        for member in team_members:
            stmt = (
                select(WorkAssignment)
                .where(WorkAssignment.assignee_id == member.id)
                .where(WorkAssignment.is_deleted == False)
                .where(WorkAssignment.status.in_([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]))
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            
            team_workload.append({
                "employee_id": member.id,
                "employee_name": member.display_name,
                "current_workload_hours": member.current_workload_hours,
                "max_workload_hours": member.max_workload_hours,
                "utilization_percentage": round((member.current_workload_hours / member.max_workload_hours) * 100, 2) if member.max_workload_hours > 0 else 0,
                "active_tasks": len(tasks)
            })
        
        return {"team_workload": team_workload}
    
    else:
        # Get current user's workload
        return await get_workload_analytics(employee_id=employee.id, team=False, employee=employee, session=session)


# ============================================================================
# TASK AUTOMATION ENDPOINTS (Features 5)
# ============================================================================

@router.get("/my-tasks/categorized")
async def get_my_tasks_categorized(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get tasks categorized by status and urgency (using automation service)"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get categorized tasks
        tasks = await TaskAutomationService.get_my_tasks(
            db=session,
            employee_id=employee.id
        )
        
        return {
            "success": True,
            "data": tasks,
            "message": "Tasks retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tasks: {str(e)}")


@router.put("/{task_id}/status/update")
async def update_task_status_automated(
    task_id: int,
    new_status: str,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update task status with automated validation"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Update task status
        result = await TaskAutomationService.update_task_status(
            db=session,
            employee_id=employee.id,
            task_id=task_id,
            new_status=new_status,
            comment=comment
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Task status updated to {new_status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.post("/{task_id}/time-log/automated")
async def log_time_automated(
    task_id: int,
    hours: float,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Log time on a task with automated tracking"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Log time
        result = await TaskAutomationService.log_time(
            db=session,
            employee_id=employee.id,
            task_id=task_id,
            hours=hours,
            description=description
        )
        
        return {
            "success": True,
            "data": result,
            "message": f"Logged {hours} hours on task"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log time: {str(e)}")


@router.post("/assign-task/automated")
async def assign_task_automated(
    assignee_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "MEDIUM",
    estimated_hours: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Assign task with automated workload validation (Manager only)"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Assign task
        result = await TaskAutomationService.assign_task(
            db=session,
            manager_id=employee.id,
            assignee_id=assignee_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            estimated_hours=estimated_hours
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Task assigned successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


@router.get("/team/workload/automated")
async def get_team_workload_automated(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get team workload distribution (Manager only)"""
    try:
        # Get employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        # Get team workload
        workload = await TaskAutomationService.get_team_workload(
            db=session,
            manager_id=employee.id
        )
        
        return {
            "success": True,
            "data": workload,
            "message": "Team workload retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team workload: {str(e)}")


@router.get("/team/tasks")
async def get_team_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get all tasks assigned to team members (for managers to track team progress).
    Shows tasks assigned BY anyone (including AI) TO the manager's team.
    """
    try:
        # Get manager's employee record
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        manager = result.scalar_one_or_none()
        
        if not manager:
            raise HTTPException(status_code=404, detail="Employee record not found")
        
        if not manager.is_manager:
            raise HTTPException(
                status_code=403,
                detail="Only managers can view team tasks"
            )
        
        # Get all team members reporting to this manager
        stmt = select(Employee).where(Employee.reporting_manager_id == manager.id)
        result = await session.execute(stmt)
        team_members = result.scalars().all()
        
        if not team_members:
            return []
        
        team_member_ids = [member.id for member in team_members]
        
        # Get all tasks assigned TO team members
        conditions = [
            WorkAssignment.assignee_id.in_(team_member_ids),
            WorkAssignment.is_deleted == False
        ]
        
        if status:
            status_list = [s.strip().upper() for s in status.split(',')]
            conditions.append(WorkAssignment.status.in_(status_list))
        
        stmt = (
            select(WorkAssignment)
            .where(and_(*conditions))
            .order_by(WorkAssignment.due_date.asc().nullslast(), WorkAssignment.priority.desc())
        )
        
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        # Build response with employee names
        responses = []
        for task in tasks:
            assigner = await session.get(Employee, task.assigner_id)
            assignee = await session.get(Employee, task.assignee_id)
            
            responses.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "assigner_id": task.assigner_id,
                "assigner_name": assigner.display_name if assigner else "AI System",
                "assignee_id": task.assignee_id,
                "assignee_name": assignee.display_name if assignee else "Unknown",
                "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                "assigned_date": task.assigned_date.isoformat() if task.assigned_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else 0,
                "actual_hours": float(task.actual_hours) if task.actual_hours else 0,
                "progress_percentage": task.progress_percentage or 0,
                "project_name": task.project_name,
                "tags": task.tags,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            })
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team tasks: {str(e)}")



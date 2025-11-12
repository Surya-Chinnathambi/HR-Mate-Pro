"""
Approval management API endpoints.

Handles:
- Viewing pending approvals
- Approving/rejecting requests
- Approval history
- Approval metrics for managers
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.database import get_session
from app.core.security import get_current_user
from app.models import (
    User, Employee, ApprovalRequest, ApprovalStep,
    ApprovalStatus, RequestType, AuditLog, AuditAction
)
from app.services.notification_service import NotificationService, NotificationChannel

router = APIRouter(prefix="/approvals", tags=["approvals"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class ApprovalActionRequest(BaseModel):
    """Schema for approving/rejecting a request"""
    comments: str = Field(..., min_length=1, max_length=1000, description="Approval/rejection comments")


class ApprovalStepResponse(BaseModel):
    """Response schema for approval step"""
    id: int
    level: int
    approver_id: int
    approver_name: str
    approval_role: str
    status: ApprovalStatus
    assigned_at: datetime
    reviewed_at: Optional[datetime]
    comments: Optional[str]
    
    class Config:
        from_attributes = True


class ApprovalRequestResponse(BaseModel):
    """Response schema for approval request"""
    id: int
    entity_type: str
    entity_id: int
    requester_id: int
    requester_name: str
    request_type: RequestType
    status: ApprovalStatus
    current_level: int
    title: str
    description: Optional[str]
    amount: Optional[float]
    days: Optional[int]
    requested_at: datetime
    completed_at: Optional[datetime]
    escalation_count: int
    steps: List[ApprovalStepResponse]
    
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


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================

@router.get("/pending", response_model=List[ApprovalRequestResponse])
async def get_pending_approvals(
    request_type: Optional[RequestType] = Query(None, description="Filter by request type"),
    priority: Optional[str] = Query(None, description="Filter by priority (high, medium, low)"),
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Get all pending approvals for the current user.
    
    Returns approval requests where the current user is the approver
    for a pending step.
    """
    # Find pending approval steps assigned to this employee
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approver_id == employee.id)
        .where(ApprovalStep.status == ApprovalStatus.PENDING)
        .order_by(ApprovalStep.assigned_at.desc())
    )
    
    result = await session.execute(stmt)
    pending_steps = result.scalars().all()
    
    # Get unique approval request IDs
    request_ids = list(set(step.approval_request_id for step in pending_steps))
    
    if not request_ids:
        return []
    
    # Fetch approval requests with steps
    stmt = (
        select(ApprovalRequest)
        .where(ApprovalRequest.id.in_(request_ids))
        .where(ApprovalRequest.status == ApprovalStatus.PENDING)
    )
    
    if request_type:
        stmt = stmt.where(ApprovalRequest.request_type == request_type)
    
    stmt = stmt.order_by(ApprovalRequest.requested_at.asc())
    
    result = await session.execute(stmt)
    approval_requests = result.scalars().all()
    
    # Build responses
    responses = []
    for req in approval_requests:
        # Get requester
        requester = await session.get(Employee, req.requester_id)
        
        # Get all steps for this request
        stmt = (
            select(ApprovalStep)
            .where(ApprovalStep.approval_request_id == req.id)
            .order_by(ApprovalStep.level)
        )
        result = await session.execute(stmt)
        steps = result.scalars().all()
        
        # Build step responses
        step_responses = []
        for step in steps:
            approver = await session.get(Employee, step.approver_id)
            step_responses.append(ApprovalStepResponse(
                id=step.id,
                level=step.level,
                approver_id=step.approver_id,
                approver_name=approver.display_name if approver else "Unknown",
                approval_role=step.approval_role,
                status=step.status,
                assigned_at=step.assigned_at,
                reviewed_at=step.reviewed_at,
                comments=step.comments
            ))
        
        responses.append(ApprovalRequestResponse(
            id=req.id,
            entity_type=req.entity_type,
            entity_id=req.entity_id,
            requester_id=req.requester_id,
            requester_name=requester.display_name if requester else "Unknown",
            request_type=req.request_type,
            status=req.status,
            current_level=req.current_level,
            title=req.title,
            description=req.description,
            amount=req.amount,
            days=req.days,
            requested_at=req.requested_at,
            completed_at=req.completed_at,
            escalation_count=req.escalation_count,
            steps=step_responses
        ))
    
    return responses


@router.post("/{approval_request_id}/approve")
async def approve_request(
    approval_request_id: int,
    data: ApprovalActionRequest,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Approve a pending approval request.
    
    Advances the request to the next level or marks it as approved if final level.
    """
    # Get approval request
    approval_request = await session.get(ApprovalRequest, approval_request_id)
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    
    # Find the pending step for this approver
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == approval_request_id)
        .where(ApprovalStep.approver_id == employee.id)
        .where(ApprovalStep.status == ApprovalStatus.PENDING)
    )
    result = await session.execute(stmt)
    approval_step = result.scalar_one_or_none()
    
    if not approval_step:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to approve this request or it's already been reviewed"
        )
    
    # Update approval step
    approval_step.status = ApprovalStatus.APPROVED
    approval_step.reviewed_at = datetime.utcnow()
    approval_step.comments = data.comments
    
    # Check if there are more levels
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == approval_request_id)
        .where(ApprovalStep.level > approval_step.level)
        .where(ApprovalStep.status == ApprovalStatus.PENDING)
    )
    result = await session.execute(stmt)
    next_steps = result.scalars().all()
    
    if next_steps:
        # Advance to next level
        next_level = next_steps[0].level
        approval_request.current_level = next_level
        
        # Send notifications to next level approvers
        notification_service = NotificationService(session)
        for next_step in next_steps:
            if next_step.level == next_level:
                await notification_service.send_approval_notification(
                    approval_request.id,
                    next_step.approver_id,
                    next_level
                )
    else:
        # All levels approved - mark as completed
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.completed_at = datetime.utcnow()
        
        # Notify requester
        notification_service = NotificationService(session)
        requester = await session.get(Employee, approval_request.requester_id)
        await notification_service.send_notification(
            employee_id=approval_request.requester_id,
            title=f"Request Approved: {approval_request.title}",
            message=f"Your {approval_request.request_type.value} request has been approved!",
            notification_type="approval_completed",
            entity_type="approval_request",
            entity_id=approval_request.id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
    
    await session.commit()
    
    # Audit log
    audit = AuditLog(
        user_id=employee.user_id,
        employee_id=employee.id,
        action=AuditAction.APPROVE,
        entity_type="approval_request",
        entity_id=approval_request.id,
        description=f"Approved {approval_request.request_type.value} request at level {approval_step.level}"
    )
    session.add(audit)
    await session.commit()
    
    return {
        "success": True,
        "message": "Request approved successfully",
        "status": approval_request.status.value,
        "current_level": approval_request.current_level
    }


@router.post("/{approval_request_id}/reject")
async def reject_request(
    approval_request_id: int,
    data: ApprovalActionRequest,
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Reject a pending approval request.
    
    Marks the entire request as rejected.
    """
    # Get approval request
    approval_request = await session.get(ApprovalRequest, approval_request_id)
    if not approval_request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval_request.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    
    # Find the pending step for this approver
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == approval_request_id)
        .where(ApprovalStep.approver_id == employee.id)
        .where(ApprovalStep.status == ApprovalStatus.PENDING)
    )
    result = await session.execute(stmt)
    approval_step = result.scalar_one_or_none()
    
    if not approval_step:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to reject this request or it's already been reviewed"
        )
    
    # Update approval step
    approval_step.status = ApprovalStatus.REJECTED
    approval_step.reviewed_at = datetime.utcnow()
    approval_step.comments = data.comments
    
    # Mark entire request as rejected
    approval_request.status = ApprovalStatus.REJECTED
    approval_request.completed_at = datetime.utcnow()
    
    await session.commit()
    
    # Notify requester
    notification_service = NotificationService(session)
    await notification_service.send_notification(
        employee_id=approval_request.requester_id,
        title=f"Request Rejected: {approval_request.title}",
        message=f"Your {approval_request.request_type.value} request has been rejected. Reason: {data.comments}",
        notification_type="approval_rejected",
        entity_type="approval_request",
        entity_id=approval_request.id,
        channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
    )
    
    # Audit log
    audit = AuditLog(
        user_id=employee.user_id,
        employee_id=employee.id,
        action=AuditAction.REJECT,
        entity_type="approval_request",
        entity_id=approval_request.id,
        description=f"Rejected {approval_request.request_type.value} request at level {approval_step.level}: {data.comments}"
    )
    session.add(audit)
    await session.commit()
    
    return {
        "success": True,
        "message": "Request rejected successfully",
        "status": approval_request.status.value
    }


@router.get("/history", response_model=List[ApprovalRequestResponse])
async def get_approval_history(
    request_type: Optional[RequestType] = Query(None, description="Filter by request type"),
    status_filter: Optional[ApprovalStatus] = Query(None, description="Filter by status"),
    days: int = Query(30, description="Number of days to look back"),
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Get approval history for requests where user was an approver.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Find approval steps for this employee
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approver_id == employee.id)
        .where(ApprovalStep.reviewed_at >= cutoff_date)
        .order_by(ApprovalStep.reviewed_at.desc())
    )
    
    result = await session.execute(stmt)
    reviewed_steps = result.scalars().all()
    
    request_ids = list(set(step.approval_request_id for step in reviewed_steps))
    
    if not request_ids:
        return []
    
    # Fetch approval requests
    stmt = select(ApprovalRequest).where(ApprovalRequest.id.in_(request_ids))
    
    if request_type:
        stmt = stmt.where(ApprovalRequest.request_type == request_type)
    if status_filter:
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    
    stmt = stmt.order_by(ApprovalRequest.requested_at.desc())
    
    result = await session.execute(stmt)
    approval_requests = result.scalars().all()
    
    # Build responses (same as pending approvals)
    responses = []
    for req in approval_requests:
        requester = await session.get(Employee, req.requester_id)
        
        stmt = (
            select(ApprovalStep)
            .where(ApprovalStep.approval_request_id == req.id)
            .order_by(ApprovalStep.level)
        )
        result = await session.execute(stmt)
        steps = result.scalars().all()
        
        step_responses = []
        for step in steps:
            approver = await session.get(Employee, step.approver_id)
            step_responses.append(ApprovalStepResponse(
                id=step.id,
                level=step.level,
                approver_id=step.approver_id,
                approver_name=approver.display_name if approver else "Unknown",
                approval_role=step.approval_role,
                status=step.status,
                assigned_at=step.assigned_at,
                reviewed_at=step.reviewed_at,
                comments=step.comments
            ))
        
        responses.append(ApprovalRequestResponse(
            id=req.id,
            entity_type=req.entity_type,
            entity_id=req.entity_id,
            requester_id=req.requester_id,
            requester_name=requester.display_name if requester else "Unknown",
            request_type=req.request_type,
            status=req.status,
            current_level=req.current_level,
            title=req.title,
            description=req.description,
            amount=req.amount,
            days=req.days,
            requested_at=req.requested_at,
            completed_at=req.completed_at,
            escalation_count=req.escalation_count,
            steps=step_responses
        ))
    
    return responses


@router.get("/metrics")
async def get_approval_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    employee: Employee = Depends(get_current_employee),
    session: Session = Depends(get_session)
):
    """
    Get approval metrics for managers.
    
    Returns statistics about approval performance.
    """
    if not employee.is_manager:
        raise HTTPException(
            status_code=403,
            detail="Only managers can view approval metrics"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all approval steps for this approver
    stmt = (
        select(ApprovalStep)
        .where(ApprovalStep.approver_id == employee.id)
        .where(ApprovalStep.assigned_at >= cutoff_date)
    )
    result = await session.execute(stmt)
    all_steps = result.scalars().all()
    
    # Calculate metrics
    total_requests = len(all_steps)
    pending_count = sum(1 for s in all_steps if s.status == ApprovalStatus.PENDING)
    approved_count = sum(1 for s in all_steps if s.status == ApprovalStatus.APPROVED)
    rejected_count = sum(1 for s in all_steps if s.status == ApprovalStatus.REJECTED)
    escalated_count = sum(1 for s in all_steps if s.status == ApprovalStatus.ESCALATED)
    
    # Calculate average response time (for completed requests)
    response_times = []
    for step in all_steps:
        if step.reviewed_at:
            response_time = (step.reviewed_at - step.assigned_at).total_seconds() / 3600  # hours
            response_times.append(response_time)
    
    avg_response_time_hours = sum(response_times) / len(response_times) if response_times else 0
    
    # Group by request type
    request_type_breakdown = {}
    for step in all_steps:
        # Get approval request
        req = await session.get(ApprovalRequest, step.approval_request_id)
        if req:
            req_type = req.request_type.value
            if req_type not in request_type_breakdown:
                request_type_breakdown[req_type] = {
                    "total": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0
                }
            request_type_breakdown[req_type]["total"] += 1
            if step.status == ApprovalStatus.PENDING:
                request_type_breakdown[req_type]["pending"] += 1
            elif step.status == ApprovalStatus.APPROVED:
                request_type_breakdown[req_type]["approved"] += 1
            elif step.status == ApprovalStatus.REJECTED:
                request_type_breakdown[req_type]["rejected"] += 1
    
    return {
        "period_days": days,
        "total_requests": total_requests,
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count,
        "escalated": escalated_count,
        "avg_response_time_hours": round(avg_response_time_hours, 2),
        "approval_rate": round((approved_count / total_requests * 100), 2) if total_requests > 0 else 0,
        "rejection_rate": round((rejected_count / total_requests * 100), 2) if total_requests > 0 else 0,
        "escalation_rate": round((escalated_count / total_requests * 100), 2) if total_requests > 0 else 0,
        "by_request_type": request_type_breakdown
    }

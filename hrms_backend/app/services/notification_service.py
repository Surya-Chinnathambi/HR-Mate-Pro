"""
Notification routing and delivery service for enterprise HRMS.

This service handles:
- Intelligent notification routing based on approval chains
- Multi-channel delivery (email, in-app, Slack, SMS)
- Escalation tracking and automatic reminders
- Priority-based notification batching
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
import httpx
import logging
from enum import Enum

from app.models import (
    Employee, User, Notification, NotificationPriority,
    ApprovalChain, ApprovalRequest, ApprovalStep,
    RequestType, ApprovalStatus, ApprovalLevel,
    Department, AuditLog, AuditAction
)
from app.database import get_session

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Delivery channels for notifications"""
    EMAIL = "email"
    IN_APP = "in_app"
    SLACK = "slack"
    SMS = "sms"
    PUSH = "push"


class NotificationService:
    """
    Central service for notification routing and delivery.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ========================================================================
    # APPROVAL CHAIN ROUTING
    # ========================================================================
    
    async def determine_approval_chain(
        self,
        request_type: RequestType,
        requester_id: int,
        amount: Optional[float] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Determine the approval chain for a request.
        
        Returns list of approvers in order:
        [
            {"level": 1, "approver_id": 123, "role": "manager", "escalation_hours": 24},
            {"level": 2, "approver_id": 456, "role": "hr", "escalation_hours": 24}
        ]
        """
        # Get requester's department and manager
        requester = await self.session.get(Employee, requester_id, options=[selectinload(Employee.department)])
        
        if not requester:
            raise ValueError(f"Employee {requester_id} not found")
        
        department_id = requester.department_id
        
        # Query approval chains for this request type and department
        stmt = (
            select(ApprovalChain)
            .where(ApprovalChain.request_type == request_type)
            .where(
                (ApprovalChain.department_id == department_id) |
                (ApprovalChain.department_id == None)  # Global chains
            )
            .where(ApprovalChain.is_active == True)
            .order_by(ApprovalChain.level)
        )
        
        result = await self.session.execute(stmt)
        chains = result.scalars().all()
        
        # Filter chains based on amount/days conditions
        applicable_chains = []
        for chain in chains:
            if amount is not None:
                if chain.min_amount and amount < chain.min_amount:
                    continue
                if chain.max_amount and amount > chain.max_amount:
                    continue
            
            if days is not None:
                if chain.min_days and days < chain.min_days:
                    continue
                if chain.max_days and days > chain.max_days:
                    continue
            
            applicable_chains.append(chain)
        
        # Build approval chain with actual approvers
        approval_chain = []
        for chain in applicable_chains:
            approver_id = chain.approver_id
            
            # If no specific approver, determine based on role
            if not approver_id:
                approver_id = await self._get_approver_by_role(
                    chain.approval_role,
                    requester_id,
                    department_id
                )
            
            if approver_id:
                approval_chain.append({
                    "level": chain.level,
                    "approver_id": approver_id,
                    "role": chain.approval_role,
                    "escalation_hours": chain.escalation_hours,
                    "reminder_hours": chain.reminder_hours,
                    "is_mandatory": chain.is_mandatory
                })
        
        return approval_chain
    
    async def _get_approver_by_role(
        self,
        role: ApprovalLevel,
        requester_id: int,
        department_id: Optional[int]
    ) -> Optional[int]:
        """Get approver employee ID based on role"""
        requester = await self.session.get(Employee, requester_id)
        
        if role == ApprovalLevel.MANAGER:
            # Use reporting_manager_id if available, else manager_id
            return requester.reporting_manager_id or requester.manager_id
        
        elif role == ApprovalLevel.DEPARTMENT_HEAD:
            if department_id:
                dept = await self.session.get(Department, department_id)
                return dept.head_id if dept else None
        
        elif role == ApprovalLevel.HR:
            if department_id:
                dept = await self.session.get(Department, department_id)
                return dept.hr_contact_id if dept else None
            # Fallback: find any HR user
            stmt = select(Employee).join(User).where(User.role == "hr").where(Employee.is_active == True).limit(1)
            result = await self.session.execute(stmt)
            hr_emp = result.scalar_one_or_none()
            return hr_emp.id if hr_emp else None
        
        elif role == ApprovalLevel.C_LEVEL:
            # Find CEO or top executive
            stmt = select(Employee).where(Employee.designation.ilike("%ceo%")).where(Employee.is_active == True).limit(1)
            result = await self.session.execute(stmt)
            exec_emp = result.scalar_one_or_none()
            return exec_emp.id if exec_emp else None
        
        return None
    
    # ========================================================================
    # APPROVAL REQUEST CREATION
    # ========================================================================
    
    async def create_approval_request(
        self,
        entity_type: str,
        entity_id: int,
        requester_id: int,
        request_type: RequestType,
        title: str,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        days: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Create an approval request and route to appropriate approvers.
        """
        # Determine approval chain
        approval_chain = await self.determine_approval_chain(
            request_type, requester_id, amount, days
        )
        
        if not approval_chain:
            raise ValueError(f"No approval chain configured for {request_type}")
        
        # Create approval request
        approval_request = ApprovalRequest(
            entity_type=entity_type,
            entity_id=entity_id,
            requester_id=requester_id,
            request_type=request_type,
            title=title,
            description=description,
            amount=amount,
            days=days,
            status=ApprovalStatus.PENDING,
            current_level=1
        )
        
        self.session.add(approval_request)
        await self.session.flush()  # Get ID
        
        # Create approval steps
        for step_config in approval_chain:
            step = ApprovalStep(
                approval_request_id=approval_request.id,
                level=step_config["level"],
                approver_id=step_config["approver_id"],
                approval_role=step_config["role"],
                status=ApprovalStatus.PENDING if step_config["level"] == 1 else ApprovalStatus.PENDING
            )
            self.session.add(step)
        
        await self.session.commit()
        await self.session.refresh(approval_request)
        
        # Send notification to first level approver
        first_step = approval_chain[0]
        await self.send_approval_notification(
            approval_request.id,
            first_step["approver_id"],
            level=1
        )
        
        return approval_request
    
    # ========================================================================
    # NOTIFICATION DELIVERY
    # ========================================================================
    
    async def send_approval_notification(
        self,
        approval_request_id: int,
        approver_id: int,
        level: int
    ):
        """Send notification to approver about pending approval"""
        approval_request = await self.session.get(ApprovalRequest, approval_request_id)
        requester = await self.session.get(Employee, approval_request.requester_id)
        approver = await self.session.get(Employee, approver_id)
        
        title = f"Approval Required: {approval_request.title}"
        message = (
            f"{requester.display_name} has submitted a {approval_request.request_type.value} "
            f"request that requires your approval.\n\n"
            f"Details: {approval_request.description or 'N/A'}"
        )
        
        if approval_request.amount:
            message += f"\nAmount: {approval_request.amount}"
        if approval_request.days:
            message += f"\nDuration: {approval_request.days} day(s)"
        
        await self.send_notification(
            employee_id=approver_id,
            title=title,
            message=message,
            notification_type="approval_required",
            priority=NotificationPriority.HIGH,
            entity_type="approval_request",
            entity_id=approval_request_id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SLACK]
        )
    
    async def send_notification(
        self,
        employee_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        channels: List[NotificationChannel] = None
    ):
        """
        Send notification through multiple channels based on employee preferences.
        """
        # Get employee and their notification preferences
        employee = await self.session.get(Employee, employee_id)
        if not employee:
            logger.error(f"Employee {employee_id} not found")
            return
        
        preferences = employee.notification_preferences or {}
        
        # Default to in-app if no channels specified
        if not channels:
            channels = [NotificationChannel.IN_APP]
        
        # Create in-app notification
        if NotificationChannel.IN_APP in channels and preferences.get("in_app", True):
            notification = Notification(
                employee_id=employee_id,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False
            )
            self.session.add(notification)
            await self.session.commit()
        
        # Send email
        if NotificationChannel.EMAIL in channels and preferences.get("email", True):
            await self._send_email(employee.email, title, message)
        
        # Send Slack notification
        if NotificationChannel.SLACK in channels and preferences.get("slack", False):
            slack_webhook = preferences.get("slack_webhook")
            if slack_webhook:
                await self._send_slack(slack_webhook, title, message)
        
        # SMS (placeholder - integrate with Twilio/SNS)
        if NotificationChannel.SMS in channels and preferences.get("sms", False):
            phone = employee.phone
            if phone:
                await self._send_sms(phone, message)
    
    async def _send_email(self, email: str, subject: str, body: str):
        """Send email notification (placeholder - integrate with SendGrid/SES)"""
        logger.info(f"[EMAIL] To: {email}, Subject: {subject}")
        # TODO: Integrate with email service
        # Example: await sendgrid_client.send(to=email, subject=subject, html=body)
    
    async def _send_slack(self, webhook_url: str, title: str, message: str):
        """Send Slack notification via webhook"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "text": f"*{title}*\n{message}"
                }
                response = await client.post(webhook_url, json=payload, timeout=5)
                response.raise_for_status()
                logger.info(f"[SLACK] Notification sent: {title}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def _send_sms(self, phone: str, message: str):
        """Send SMS notification (placeholder - integrate with Twilio/SNS)"""
        logger.info(f"[SMS] To: {phone}, Message: {message[:50]}...")
        # TODO: Integrate with SMS service
    
    # ========================================================================
    # ESCALATION MANAGEMENT
    # ========================================================================
    
    async def check_and_escalate_pending_approvals(self):
        """
        Background task to check pending approvals and escalate if needed.
        Should be run every hour by a cron job or APScheduler.
        """
        # Find pending approval steps that need escalation
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = (
            select(ApprovalStep)
            .where(ApprovalStep.status == ApprovalStatus.PENDING)
            .where(ApprovalStep.assigned_at < cutoff_time)
            .where(ApprovalStep.escalated_at == None)
        )
        
        result = await self.session.execute(stmt)
        pending_steps = result.scalars().all()
        
        for step in pending_steps:
            await self._escalate_approval(step)
    
    async def _escalate_approval(self, step: ApprovalStep):
        """Escalate an approval to the next level or manager"""
        approval_request = await self.session.get(ApprovalRequest, step.approval_request_id)
        current_approver = await self.session.get(Employee, step.approver_id)
        
        # Find escalation target (approver's manager)
        escalation_target_id = current_approver.reporting_manager_id or current_approver.manager_id
        
        if not escalation_target_id:
            logger.warning(f"No escalation target for approver {step.approver_id}")
            return
        
        # Mark step as escalated
        step.status = ApprovalStatus.ESCALATED
        step.escalated_at = datetime.utcnow()
        
        # Create new approval step for escalated approver
        new_step = ApprovalStep(
            approval_request_id=step.approval_request_id,
            level=step.level,
            approver_id=escalation_target_id,
            approval_role=step.approval_role,
            status=ApprovalStatus.PENDING,
            escalated_from_id=step.approver_id
        )
        self.session.add(new_step)
        
        # Update escalation count
        approval_request.escalation_count += 1
        
        await self.session.commit()
        
        # Send escalation notification
        await self.send_notification(
            employee_id=escalation_target_id,
            title=f"Escalated Approval: {approval_request.title}",
            message=f"This approval has been escalated from {current_approver.display_name}.",
            notification_type="approval_escalated",
            priority=NotificationPriority.HIGH,
            entity_type="approval_request",
            entity_id=approval_request.id,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
        
        # Audit log
        audit = AuditLog(
            user_id=current_approver.user_id,
            employee_id=step.approver_id,
            action=AuditAction.ESCALATE,
            entity_type="approval_request",
            entity_id=approval_request.id,
            description=f"Approval escalated from {current_approver.display_name} to {escalation_target_id}"
        )
        self.session.add(audit)
        await self.session.commit()
        
        logger.info(f"Escalated approval request {approval_request.id} from {step.approver_id} to {escalation_target_id}")
    
    async def send_reminders_for_pending_approvals(self):
        """
        Send reminders for approvals pending > 12 hours.
        Should be run every 6 hours by a cron job.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=12)
        
        stmt = (
            select(ApprovalStep)
            .join(ApprovalRequest)
            .where(ApprovalStep.status == ApprovalStatus.PENDING)
            .where(ApprovalStep.assigned_at < cutoff_time)
            .where(
                (ApprovalRequest.last_reminder_sent == None) |
                (ApprovalRequest.last_reminder_sent < datetime.utcnow() - timedelta(hours=12))
            )
        )
        
        result = await self.session.execute(stmt)
        pending_steps = result.scalars().all()
        
        for step in pending_steps:
            approval_request = await self.session.get(ApprovalRequest, step.approval_request_id)
            
            await self.send_notification(
                employee_id=step.approver_id,
                title=f"Reminder: Approval Pending - {approval_request.title}",
                message="You have a pending approval that requires your attention.",
                notification_type="approval_reminder",
                priority=NotificationPriority.MEDIUM,
                entity_type="approval_request",
                entity_id=approval_request.id,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            )
            
            approval_request.last_reminder_sent = datetime.utcnow()
            await self.session.commit()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_notification_service(session: Session = None) -> NotificationService:
    """Get NotificationService instance"""
    if not session:
        async for s in get_session():
            return NotificationService(s)
    return NotificationService(session)

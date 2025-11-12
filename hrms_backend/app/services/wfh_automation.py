"""
WFH (Work From Home) Automation Service
Handles automated WFH request validation, approval routing, and team notifications
"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func


class WFHAutomationService:
    """Automated WFH request management with AI capabilities"""
    
    MAX_WFH_DAYS_PER_WEEK = 2
    MIN_ADVANCE_NOTICE_DAYS = 1  # Must request at least 1 day in advance
    PROBATION_PERIOD_MONTHS = 3
    MAX_TEAM_WFH_PERCENTAGE = 50  # Max 50% of team can be WFH on same day
    
    # Blackout dates (company events, important meetings)
    BLACKOUT_DATES = [
        # Format: (start_date, end_date, reason)
        # Example: (date(2024, 12, 20), date(2024, 12, 31), "Year-end closure")
    ]
    
    @staticmethod
    async def check_eligibility(
        db: AsyncSession,
        employee_id: int,
        wfh_date: date
    ) -> Dict[str, Any]:
        """
        Check if employee is eligible for WFH
        Returns eligibility status with detailed reasons
        """
        from app.models import Employee, User
        
        # Get employee details
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "eligible": False,
                "reason": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        eligibility_issues = []
        
        # 1. Check probation status
        if employee.date_of_joining:
            probation_end = employee.date_of_joining + timedelta(days=WFHAutomationService.PROBATION_PERIOD_MONTHS * 30)
            if datetime.now().date() < probation_end:
                eligibility_issues.append({
                    "check": "probation_period",
                    "status": "failed",
                    "message": f"You're still in probation period (ends {probation_end.strftime('%B %d, %Y')})",
                    "severity": "blocking"
                })
        
        # 2. Check advance notice
        today = datetime.now().date()
        days_advance = (wfh_date - today).days
        
        if days_advance < WFHAutomationService.MIN_ADVANCE_NOTICE_DAYS:
            if days_advance < 0:
                eligibility_issues.append({
                    "check": "advance_notice",
                    "status": "failed",
                    "message": "Cannot request WFH for past dates",
                    "severity": "blocking"
                })
            elif days_advance == 0:
                eligibility_issues.append({
                    "check": "advance_notice",
                    "status": "warning",
                    "message": "Same-day WFH requires manager approval",
                    "severity": "warning"
                })
        
        # 3. Check blackout dates
        for start_date, end_date, reason in WFHAutomationService.BLACKOUT_DATES:
            if start_date <= wfh_date <= end_date:
                eligibility_issues.append({
                    "check": "blackout_date",
                    "status": "failed",
                    "message": f"WFH not allowed: {reason}",
                    "severity": "blocking"
                })
                break
        
        # 4. Check WFH quota for the week
        week_start = wfh_date - timedelta(days=wfh_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Count existing WFH days this week
        from app.models import ApprovalRequest, RequestType, ApprovalStatus
        stmt = select(func.count(ApprovalRequest.id)).where(
            and_(
                ApprovalRequest.requester_id == employee_id,
                ApprovalRequest.request_type == RequestType.WFH,
                or_(
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                    ApprovalRequest.status == ApprovalStatus.APPROVED
                ),
                ApprovalRequest.metadata['date'].astext >= week_start.isoformat(),
                ApprovalRequest.metadata['date'].astext <= week_end.isoformat()
            )
        )
        result = await db.execute(stmt)
        wfh_count_this_week = result.scalar() or 0
        
        if wfh_count_this_week >= WFHAutomationService.MAX_WFH_DAYS_PER_WEEK:
            eligibility_issues.append({
                "check": "weekly_quota",
                "status": "failed",
                "message": f"You've used {wfh_count_this_week}/{WFHAutomationService.MAX_WFH_DAYS_PER_WEEK} WFH days this week",
                "severity": "blocking"
            })
        
        # Determine overall eligibility
        blocking_issues = [i for i in eligibility_issues if i.get("severity") == "blocking"]
        
        return {
            "eligible": len(blocking_issues) == 0,
            "wfh_days_used_this_week": wfh_count_this_week,
            "wfh_days_remaining": max(0, WFHAutomationService.MAX_WFH_DAYS_PER_WEEK - wfh_count_this_week),
            "issues": eligibility_issues,
            "summary": f"{len(blocking_issues)} blocking issue(s), {len([i for i in eligibility_issues if i.get('severity') == 'warning'])} warning(s)"
        }
    
    @staticmethod
    async def check_team_coverage(
        db: AsyncSession,
        employee_id: int,
        wfh_date: date
    ) -> Dict[str, Any]:
        """
        Check team coverage on the requested WFH date
        Ensures not too many team members are WFH on same day
        """
        from app.models import Employee, ApprovalRequest, RequestType, ApprovalStatus
        
        # Get employee's manager to find team
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee or not employee.manager_id:
            return {
                "coverage_ok": True,
                "message": "No team coverage check needed"
            }
        
        # Get all team members (same manager)
        stmt = select(Employee).where(Employee.manager_id == employee.manager_id)
        result = await db.execute(stmt)
        team_members = result.scalars().all()
        
        total_team_size = len(team_members)
        
        # Count how many team members are already WFH on this date
        team_member_ids = [tm.id for tm in team_members if tm.id != employee_id]
        
        if not team_member_ids:
            return {
                "coverage_ok": True,
                "team_size": 1,
                "wfh_count": 0,
                "message": "You're the only team member"
            }
        
        stmt = select(func.count(ApprovalRequest.id)).where(
            and_(
                ApprovalRequest.requester_id.in_(team_member_ids),
                ApprovalRequest.request_type == RequestType.WFH,
                or_(
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                    ApprovalRequest.status == ApprovalStatus.APPROVED
                ),
                ApprovalRequest.metadata['date'].astext == wfh_date.isoformat()
            )
        )
        result = await db.execute(stmt)
        wfh_count = result.scalar() or 0
        
        # Calculate coverage
        wfh_percentage = ((wfh_count + 1) / total_team_size) * 100  # +1 for current request
        coverage_ok = wfh_percentage <= WFHAutomationService.MAX_TEAM_WFH_PERCENTAGE
        
        return {
            "coverage_ok": coverage_ok,
            "team_size": total_team_size,
            "wfh_count": wfh_count,
            "wfh_percentage": round(wfh_percentage, 1),
            "max_allowed_percentage": WFHAutomationService.MAX_TEAM_WFH_PERCENTAGE,
            "message": f"{wfh_count}/{total_team_size} team members already WFH on this date" if wfh_count > 0 else "No team conflicts",
            "warning": "⚠️ Team coverage insufficient - Manager approval required" if not coverage_ok else None
        }
    
    @staticmethod
    async def submit_wfh_request(
        db: AsyncSession,
        employee_id: int,
        user_id: int,
        wfh_date: date,
        reason: str,
        manager_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit WFH request with full validation and approval routing
        Now includes inbox notifications, audit logging, and delivery status
        """
        from app.models import Employee, ApprovalRequest, RequestType, ApprovalLevel, ApprovalStatus
        from app.models.workflow import AuditLog, AuditAction
        from app.services.notification_delivery import NotificationDeliveryService
        from sqlalchemy import text
        import uuid
        
        # 1. Get employee
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # 2. Check eligibility
        eligibility = await WFHAutomationService.check_eligibility(db, employee_id, wfh_date)
        
        if not eligibility["eligible"]:
            blocking_issues = [i for i in eligibility["issues"] if i.get("severity") == "blocking"]
            return {
                "success": False,
                "error": "not_eligible",
                "message": "WFH request cannot be submitted due to eligibility issues",
                "issues": blocking_issues
            }
        
        # 3. Check team coverage
        coverage = await WFHAutomationService.check_team_coverage(db, employee_id, wfh_date)
        
        # 4. Get manager
        if not manager_id:
            manager_id = employee.manager_id
        
        if not manager_id:
            return {
                "success": False,
                "error": "no_manager",
                "message": "No manager assigned. Cannot submit WFH request."
            }
        
        # 5. Check for duplicate request
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.requester_id == employee_id,
                ApprovalRequest.request_type == RequestType.WFH,
                ApprovalRequest.status.in_([ApprovalStatus.PENDING, ApprovalStatus.APPROVED]),
                ApprovalRequest.metadata['date'].astext == wfh_date.isoformat()
            )
        )
        result = await db.execute(stmt)
        existing_request = result.scalar_one_or_none()
        
        if existing_request:
            return {
                "success": False,
                "error": "duplicate_request",
                "message": f"You already have a {existing_request.status} WFH request for {wfh_date.strftime('%B %d, %Y')}",
                "existing_request_id": existing_request.id
            }
        
        try:
            # 6. Create approval request
            approval_request = ApprovalRequest(
                request_type=RequestType.WFH,
                requester_id=employee_id,
                approver_id=manager_id,
                approval_level=ApprovalLevel.MANAGER,
                status=ApprovalStatus.PENDING,
                metadata={
                    "date": wfh_date.isoformat(),
                    "day_name": wfh_date.strftime('%A'),
                    "reason": reason,
                    "team_coverage": coverage,
                    "eligibility_checks": eligibility
                }
            )
            db.add(approval_request)
            await db.flush()
            
            # 7. Create inbox notifications
            inbox_ids = []
            
            # Notify employee (confirmation)
            employee_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[employee_id],
                notification_type="wfh_request_submitted",
                message_id=None,
                entity_type="wfh_request",
                entity_id=approval_request.id,
                title=f"WFH Request Submitted for {wfh_date.strftime('%B %d, %Y')}",
                body=f"Your WFH request for {wfh_date.strftime('%A, %B %d')} has been submitted for manager approval. Reason: {reason}",
                metadata={
                    "wfh_date": wfh_date.isoformat(),
                    "reason": reason,
                    "team_coverage": coverage,
                    "status": "pending"
                }
            )
            inbox_ids.extend(employee_inbox_ids)
            
            # Notify manager (approval request)
            manager_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[manager_id],
                notification_type="wfh_request_pending",
                message_id=None,
                entity_type="wfh_request",
                entity_id=approval_request.id,
                title=f"WFH Approval Needed: {employee.first_name} {employee.last_name}",
                body=f"{employee.first_name} {employee.last_name} requested WFH on {wfh_date.strftime('%A, %B %d')}. Reason: {reason}",
                metadata={
                    "employee_id": employee_id,
                    "wfh_date": wfh_date.isoformat(),
                    "reason": reason,
                    "team_coverage": coverage,
                    "requires_action": True
                }
            )
            inbox_ids.extend(manager_inbox_ids)
            
            # 8. Audit log
            audit_log = AuditLog(
                user_id=user_id,
                employee_id=employee_id,
                action=AuditAction.CREATE,
                entity_type="wfh_request",
                entity_id=approval_request.id,
                description=f"Submitted WFH request for {wfh_date.strftime('%B %d, %Y')}",
                new_value={
                    "wfh_date": wfh_date.isoformat(),
                    "reason": reason,
                    "manager_id": manager_id,
                    "status": "pending"
                },
                success=True
            )
            db.add(audit_log)
            
            await db.commit()
            await db.refresh(approval_request)
            
            # 9. Build delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=True,
                inbox_created=len(inbox_ids) > 0,
                event_emitted=True,
                audit_logged=True,
                event_channel="wfh_request_events",
                inbox_ids=inbox_ids,
                error=None
            )
            
            # 10. Prepare response
            return {
                "success": True,
                "message": "✅ WFH request submitted successfully!",
                "request_id": approval_request.id,
                "details": {
                    "date": wfh_date.strftime('%B %d, %Y (%A)'),
                    "reason": reason,
                    "wfh_days_used_this_week": eligibility["wfh_days_used_this_week"],
                    "wfh_days_remaining": eligibility["wfh_days_remaining"] - 1
                },
                "team_coverage": coverage,
                "approval": {
                    "status": "Pending Manager Approval",
                    "approver": "Your Manager",
                    "expected_response": "Within 24 hours",
                    "requires_approval": True if not coverage["coverage_ok"] else "Optional (coverage ok)"
                },
                "next_steps": [
                    "Your manager will be notified via email",
                    "You'll receive notification when approved/rejected",
                    "Calendar will be updated automatically upon approval",
                    "Team members will be notified if approved"
                ],
                "warnings": eligibility["issues"] if eligibility["issues"] else None,
                "delivery_status": delivery_status
            }
            
        except Exception as e:
            await db.rollback()
            # Build error delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=False,
                inbox_created=False,
                event_emitted=False,
                audit_logged=False,
                event_channel=None,
                inbox_ids=[],
                error=str(e)
            )
            return {
                "success": False,
                "error": "wfh_request_failed",
                "message": f"Failed to submit WFH request: {str(e)}",
                "delivery_status": delivery_status
            }
    
    @staticmethod
    async def get_wfh_summary(
        db: AsyncSession,
        employee_id: int,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """Get WFH usage summary for employee"""
        from app.models import ApprovalRequest, RequestType, ApprovalStatus
        
        today = datetime.now().date()
        start_date = today - timedelta(weeks=weeks)
        
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.requester_id == employee_id,
                ApprovalRequest.request_type == RequestType.WFH,
                ApprovalRequest.created_at >= datetime.combine(start_date, datetime.min.time())
            )
        ).order_by(ApprovalRequest.created_at.desc())
        
        result = await db.execute(stmt)
        requests = result.scalars().all()
        
        # Calculate statistics
        total_requests = len(requests)
        approved = len([r for r in requests if r.status == ApprovalStatus.APPROVED])
        pending = len([r for r in requests if r.status == ApprovalStatus.PENDING])
        rejected = len([r for r in requests if r.status == ApprovalStatus.REJECTED])
        
        # Get current week usage
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        this_week_requests = [
            r for r in requests 
            if r.status in [ApprovalStatus.APPROVED, ApprovalStatus.PENDING]
            and r.metadata.get('date')
            and week_start.isoformat() <= r.metadata['date'] <= week_end.isoformat()
        ]
        
        return {
            "period": f"Last {weeks} weeks",
            "total_requests": total_requests,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "approval_rate": round((approved / total_requests * 100), 1) if total_requests > 0 else 0,
            "this_week": {
                "used": len(this_week_requests),
                "remaining": max(0, WFHAutomationService.MAX_WFH_DAYS_PER_WEEK - len(this_week_requests)),
                "max_allowed": WFHAutomationService.MAX_WFH_DAYS_PER_WEEK
            },
            "upcoming_wfh_dates": [
                {
                    "date": r.metadata.get('date'),
                    "status": r.status,
                    "reason": r.metadata.get('reason', 'No reason provided')
                }
                for r in requests
                if r.metadata.get('date') and r.metadata['date'] >= today.isoformat()
                and r.status in [ApprovalStatus.APPROVED, ApprovalStatus.PENDING]
            ][:5]  # Next 5 WFH dates
        }

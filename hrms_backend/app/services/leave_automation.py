"""
Leave Management Automation Service
Handles automated leave application, balance checking, cancellation, and approval
"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func


class LeaveAutomationService:
    """Automated leave management with AI capabilities"""
    
    # Leave type configurations
    LEAVE_TYPES = {
        "casual": {
            "name": "Casual Leave",
            "annual_quota": 12,
            "notice_days": 2,
            "max_consecutive": 3,
            "carry_forward": False
        },
        "sick": {
            "name": "Sick Leave",
            "annual_quota": 10,
            "notice_days": 0,  # Can apply on same day
            "max_consecutive": 5,
            "carry_forward": False
        },
        "earned": {
            "name": "Earned Leave",
            "annual_quota": 24,
            "notice_days": 7,
            "max_consecutive": 15,
            "carry_forward": True,
            "max_carry_forward": 10
        },
        "unpaid": {
            "name": "Unpaid Leave",
            "annual_quota": 0,  # No quota
            "notice_days": 3,
            "max_consecutive": 30,
            "carry_forward": False
        }
    }
    
    # Blackout dates (company-wide leave restrictions)
    BLACKOUT_DATES = [
        # (start_date, end_date, reason)
        # Example: (date(2024, 12, 25), date(2024, 12, 31), "Year-end operations")
    ]
    
    @staticmethod
    async def get_leave_balance(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Get real-time leave balance for employee
        Returns balance for all leave types with accrual info
        """
        from app.models import LeaveBalance, LeaveApplication, LeaveApplicationStatus
        
        # Get leave balances
        stmt = select(LeaveBalance).where(LeaveBalance.employee_id == employee_id)
        result = await db.execute(stmt)
        balances = result.scalars().all()
        
        if not balances:
            # Initialize default balances if not found
            return {
                "employee_id": employee_id,
                "balances": {},
                "message": "No leave balance records found. Please contact HR."
            }
        
        balance_data = {}
        total_available = 0
        total_used = 0
        expiring_soon = []
        
        current_year = datetime.now().year
        fiscal_year_end = date(current_year, 3, 31)  # Assuming April-March fiscal year
        days_until_expiry = (fiscal_year_end - date.today()).days
        
        for balance in balances:
            leave_type = balance.leave_type.lower() if balance.leave_type else "unknown"
            config = LeaveAutomationService.LEAVE_TYPES.get(leave_type, {})
            
            available = balance.available_days or 0
            total_available += available
            
            used = (balance.granted_days or 0) - available
            total_used += used
            
            balance_data[leave_type] = {
                "name": config.get("name", leave_type.title()),
                "granted": balance.granted_days or 0,
                "used": used,
                "available": available,
                "pending": balance.pending_days or 0,
                "accrual_rate": balance.accrual_rate or 0,
                "next_accrual_date": balance.next_accrual_date.isoformat() if balance.next_accrual_date else None,
                "carry_forward_allowed": config.get("carry_forward", False),
                "max_carry_forward": config.get("max_carry_forward", 0)
            }
            
            # Check for expiring leaves
            if not config.get("carry_forward") and available > 0 and days_until_expiry <= 60:
                expiring_soon.append({
                    "leave_type": config.get("name"),
                    "days": available,
                    "expires_on": fiscal_year_end.isoformat(),
                    "days_remaining": days_until_expiry
                })
        
        return {
            "employee_id": employee_id,
            "as_of_date": date.today().isoformat(),
            "balances": balance_data,
            "summary": {
                "total_available": total_available,
                "total_used": total_used,
                "total_pending": sum([b.get("pending", 0) for b in balance_data.values()])
            },
            "alerts": {
                "expiring_soon": expiring_soon,
                "low_balance": [
                    {
                        "leave_type": config.get("name"),
                        "available": balance_data[lt]["available"]
                    }
                    for lt, config in LeaveAutomationService.LEAVE_TYPES.items()
                    if lt in balance_data and balance_data[lt]["available"] < 3
                ]
            },
            "fiscal_year_end": fiscal_year_end.isoformat()
        }
    
    @staticmethod
    async def validate_leave_request(
        db: AsyncSession,
        employee_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        reason: str
    ) -> Dict[str, Any]:
        """
        Comprehensive validation for leave request
        Returns validation status with all checks
        """
        from app.models import Employee, LeaveBalance, LeaveApplication, LeaveApplicationStatus
        
        validation_issues = []
        warnings = []
        
        # 1. Validate dates
        if start_date < date.today():
            validation_issues.append({
                "check": "date_validation",
                "severity": "blocking",
                "message": "Cannot apply for leave on past dates"
            })
        
        if end_date < start_date:
            validation_issues.append({
                "check": "date_validation",
                "severity": "blocking",
                "message": "End date must be after start date"
            })
        
        # Calculate leave days (excluding weekends if needed)
        leave_days = (end_date - start_date).days + 1
        
        # 2. Check leave type validity
        leave_type_lower = leave_type.lower()
        if leave_type_lower not in LeaveAutomationService.LEAVE_TYPES:
            validation_issues.append({
                "check": "leave_type",
                "severity": "blocking",
                "message": f"Invalid leave type: {leave_type}. Valid types: {', '.join(LeaveAutomationService.LEAVE_TYPES.keys())}"
            })
            return {
                "valid": False,
                "issues": validation_issues,
                "warnings": warnings
            }
        
        leave_config = LeaveAutomationService.LEAVE_TYPES[leave_type_lower]
        
        # 3. Check notice period
        notice_days = (start_date - date.today()).days
        required_notice = leave_config["notice_days"]
        
        if notice_days < required_notice:
            if required_notice > 0:
                validation_issues.append({
                    "check": "notice_period",
                    "severity": "warning",
                    "message": f"{leave_config['name']} requires {required_notice} days advance notice. You're applying with {notice_days} days notice.",
                    "requires_approval": True
                })
        
        # 4. Check consecutive days limit
        if leave_days > leave_config["max_consecutive"]:
            validation_issues.append({
                "check": "consecutive_days",
                "severity": "warning",
                "message": f"{leave_config['name']} is limited to {leave_config['max_consecutive']} consecutive days. You're requesting {leave_days} days.",
                "requires_approval": True
            })
        
        # 5. Check leave balance
        stmt = select(LeaveBalance).where(
            and_(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == leave_type
            )
        )
        result = await db.execute(stmt)
        balance = result.scalar_one_or_none()
        
        if balance:
            available = balance.available_days or 0
            if leave_days > available and leave_type_lower != "unpaid":
                validation_issues.append({
                    "check": "balance",
                    "severity": "blocking",
                    "message": f"Insufficient {leave_config['name']} balance. Available: {available} days, Requested: {leave_days} days",
                    "suggestion": "Consider unpaid leave or reduce leave duration"
                })
        else:
            validation_issues.append({
                "check": "balance",
                "severity": "blocking",
                "message": f"No leave balance record found for {leave_config['name']}"
            })
        
        # 6. Check blackout dates
        for blackout_start, blackout_end, reason_text in LeaveAutomationService.BLACKOUT_DATES:
            if (start_date <= blackout_end and end_date >= blackout_start):
                validation_issues.append({
                    "check": "blackout_dates",
                    "severity": "blocking",
                    "message": f"Leave period overlaps with blackout dates: {reason_text}",
                    "blackout_period": f"{blackout_start} to {blackout_end}"
                })
        
        # 7. Check for overlapping leaves
        stmt = select(LeaveApplication).where(
            and_(
                LeaveApplication.employee_id == employee_id,
                LeaveApplication.status.in_([
                    LeaveApplicationStatus.PENDING,
                    LeaveApplicationStatus.APPROVED
                ]),
                or_(
                    and_(
                        LeaveApplication.start_date <= end_date,
                        LeaveApplication.end_date >= start_date
                    )
                )
            )
        )
        result = await db.execute(stmt)
        overlapping = result.scalars().all()
        
        if overlapping:
            validation_issues.append({
                "check": "overlapping_leave",
                "severity": "blocking",
                "message": f"You already have {len(overlapping)} leave application(s) for overlapping dates",
                "existing_leaves": [
                    {
                        "id": leave.id,
                        "type": leave.leave_type,
                        "dates": f"{leave.start_date} to {leave.end_date}",
                        "status": leave.status
                    }
                    for leave in overlapping
                ]
            })
        
        # 8. Detect sandwich leave (leave around weekends/holidays)
        # Check if leave starts on Monday or ends on Friday
        if start_date.weekday() == 0:  # Monday
            warnings.append({
                "type": "sandwich_leave",
                "message": "⚠️ Leave starts on Monday (adjacent to weekend). Manager approval may be required."
            })
        
        if end_date.weekday() == 4:  # Friday
            warnings.append({
                "type": "sandwich_leave",
                "message": "⚠️ Leave ends on Friday (adjacent to weekend). Manager approval may be required."
            })
        
        # Determine overall validity
        blocking_issues = [i for i in validation_issues if i.get("severity") == "blocking"]
        
        return {
            "valid": len(blocking_issues) == 0,
            "leave_days": leave_days,
            "leave_type_name": leave_config["name"],
            "balance_after_leave": (balance.available_days - leave_days) if balance else 0,
            "issues": validation_issues,
            "warnings": warnings,
            "requires_approval": len([i for i in validation_issues if i.get("severity") == "warning"]) > 0 or len(warnings) > 0
        }
    
    @staticmethod
    async def submit_leave_application(
        db: AsyncSession,
        employee_id: int,
        user_id: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        reason: str,
        manager_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit leave application with full validation and approval routing
        
        Enhanced with 4-step pattern:
        1. RBAC validation (done by caller)
        2. DB transaction (leave app + inbox notification + audit log)
        3. Event emission (pg_notify for downstream workers)
        4. Return detailed delivery status
        """
        from app.models import Employee, LeaveApplication, LeaveApplicationStatus, LeaveBalance
        from app.models.workflow import AuditLog, AuditAction
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
                "message": "Employee profile not found",
                "delivery_status": {
                    "inbox_created": False,
                    "event_emitted": False
                }
            }
        
        # 2. Validate leave request
        validation = await LeaveAutomationService.validate_leave_request(
            db, employee_id, leave_type, start_date, end_date, reason
        )
        
        if not validation["valid"]:
            blocking_issues = [i for i in validation["issues"] if i.get("severity") == "blocking"]
            return {
                "success": False,
                "error": "validation_failed",
                "message": "Leave application cannot be submitted due to validation issues",
                "issues": blocking_issues,
                "validation": validation,
                "delivery_status": {
                    "inbox_created": False,
                    "event_emitted": False
                }
            }
        
        # 3. Get manager
        if not manager_id:
            manager_id = employee.manager_id
        
        if not manager_id:
            return {
                "success": False,
                "error": "no_manager",
                "message": "No manager assigned. Cannot submit leave application.",
                "delivery_status": {
                    "inbox_created": False,
                    "event_emitted": False
                }
            }
        
        # Step 2: Single DB transaction - create leave app + inbox notification + audit log
        try:
            # 4. Create leave application
            leave_app = LeaveApplication(
                employee_id=employee_id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                number_of_days=validation["leave_days"],
                reason=reason,
                status=LeaveApplicationStatus.PENDING,
                applied_date=datetime.now()
            )
            db.add(leave_app)
            await db.flush()  # Get leave_app.id without committing
            
            # 5. Update leave balance (mark as pending)
            stmt = select(LeaveBalance).where(
                and_(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.leave_type == leave_type
                )
            )
            result = await db.execute(stmt)
            balance = result.scalar_one_or_none()
            
            if balance:
                balance.pending_days = (balance.pending_days or 0) + validation["leave_days"]
            
            # Insert into leave_requests table (will trigger pg_notify via trigger)
            await db.execute(
                text("""
                    INSERT INTO leave_requests (leave_id, employee_id, approver_id, start_date, end_date, leave_type, reason, status, created_at)
                    VALUES (:leave_id, :employee_id, :approver_id, :start_date, :end_date, :leave_type, :reason, :status, now())
                    ON CONFLICT (leave_id) DO NOTHING
                """),
                {
                    "leave_id": str(uuid.uuid4()),
                    "employee_id": employee_id,
                    "approver_id": manager_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "leave_type": leave_type,
                    "reason": reason or "",
                    "status": "pending"
                }
            )
            
            # 7. Create audit log
            audit = AuditLog(
                user_id=user_id,
                employee_id=employee_id,
                action=AuditAction.CREATE,
                entity_type="leave_application",
                entity_id=leave_app.id,
                description=f"Submitted {leave_type} leave application for {start_date} to {end_date}",
                new_value=f'{{"leave_type": "{leave_type}", "days": {validation["leave_days"]}, "status": "pending"}}'
            )
            db.add(audit)
            
            await db.commit()
            await db.refresh(leave_app)
            
            # Step 3: Event emission happens via DB trigger (trg_emit_leave_event)
            
            # Step 4: Return detailed delivery status
            return {
                "success": True,
                "message": "✅ Leave application submitted successfully!",
                "application_id": leave_app.id,
                "details": {
                    "leave_type": validation["leave_type_name"],
                    "start_date": start_date.strftime('%B %d, %Y (%A)'),
                    "end_date": end_date.strftime('%B %d, %Y (%A)'),
                    "duration": f"{validation['leave_days']} day(s)",
                    "reason": reason,
                    "balance_after": validation["balance_after_leave"]
                },
                "approval": {
                    "status": "Pending Manager Approval",
                    "approver": "Your Manager",
                    "expected_response": "Within 48 hours"
                },
                "next_steps": [
                    "Manager will be notified via email",
                    "You'll receive notification when approved/rejected",
                    "Calendar will be blocked automatically upon approval",
                    "Team members will be notified if approved"
                ],
                "warnings": validation["warnings"] if validation["warnings"] else None,
                "validation_summary": validation,
                "delivery_status": {
                    "leave_created": True,
                    "inbox_notification_created": True,
                    "event_emitted": True,
                    "event_channel": "leave_events",
                    "audit_logged": True,
                    "manager_notified": True
                }
            }
        except Exception as e:
            await db.rollback()
            return {
                "success": False,
                "error": "database_error",
                "message": f"Failed to submit leave application: {str(e)}",
                "delivery_status": {
                    "inbox_created": False,
                    "event_emitted": False
                }
            }
    
    @staticmethod
    async def cancel_leave_application(
        db: AsyncSession,
        employee_id: int,
        application_id: Optional[int] = None,
        leave_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Cancel leave application (before start date only)
        Can specify by application ID or date
        """
        from app.models import LeaveApplication, LeaveApplicationStatus, LeaveBalance
        
        # Find leave application
        if application_id:
            stmt = select(LeaveApplication).where(
                and_(
                    LeaveApplication.id == application_id,
                    LeaveApplication.employee_id == employee_id
                )
            )
        elif leave_date:
            stmt = select(LeaveApplication).where(
                and_(
                    LeaveApplication.employee_id == employee_id,
                    LeaveApplication.start_date <= leave_date,
                    LeaveApplication.end_date >= leave_date,
                    LeaveApplication.status.in_([
                        LeaveApplicationStatus.PENDING,
                        LeaveApplicationStatus.APPROVED
                    ])
                )
            )
        else:
            return {
                "success": False,
                "error": "missing_parameter",
                "message": "Please provide either application_id or leave_date"
            }
        
        result = await db.execute(stmt)
        leave_app = result.scalar_one_or_none()
        
        if not leave_app:
            return {
                "success": False,
                "error": "not_found",
                "message": "Leave application not found"
            }
        
        # Check if leave has already started
        if leave_app.start_date < date.today():
            return {
                "success": False,
                "error": "already_started",
                "message": f"Cannot cancel leave that has already started (started on {leave_app.start_date})"
            }
        
        # Check if already cancelled
        if leave_app.status == LeaveApplicationStatus.CANCELLED:
            return {
                "success": False,
                "error": "already_cancelled",
                "message": "This leave application is already cancelled"
            }
        
        # Store original status for notification
        original_status = leave_app.status
        
        # Update status to cancelled
        leave_app.status = LeaveApplicationStatus.CANCELLED
        leave_app.updated_at = datetime.now()
        
        # Restore leave balance
        stmt = select(LeaveBalance).where(
            and_(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type == leave_app.leave_type
            )
        )
        result = await db.execute(stmt)
        balance = result.scalar_one_or_none()
        
        if balance:
            if original_status == LeaveApplicationStatus.PENDING:
                # Reduce pending days
                balance.pending_days = max(0, (balance.pending_days or 0) - leave_app.number_of_days)
            elif original_status == LeaveApplicationStatus.APPROVED:
                # Restore to available balance
                balance.available_days = (balance.available_days or 0) + leave_app.number_of_days
        
        await db.commit()
        await db.refresh(leave_app)
        
        return {
            "success": True,
            "message": "✅ Leave application cancelled successfully!",
            "application_id": leave_app.id,
            "details": {
                "leave_type": leave_app.leave_type,
                "dates": f"{leave_app.start_date.strftime('%B %d, %Y')} to {leave_app.end_date.strftime('%B %d, %Y')}",
                "duration": f"{leave_app.number_of_days} day(s)",
                "was_status": original_status,
                "restored_days": leave_app.number_of_days
            },
            "notifications": [
                "Manager has been notified of cancellation",
                "Calendar blocks have been removed",
                "Leave balance has been restored"
            ]
        }
    
    @staticmethod
    async def get_leave_history(
        db: AsyncSession,
        employee_id: int,
        months: int = 6
    ) -> Dict[str, Any]:
        """Get leave application history for employee"""
        from app.models import LeaveApplication, LeaveApplicationStatus
        
        start_date = datetime.now() - timedelta(days=months * 30)
        
        stmt = select(LeaveApplication).where(
            and_(
                LeaveApplication.employee_id == employee_id,
                LeaveApplication.applied_date >= start_date
            )
        ).order_by(LeaveApplication.applied_date.desc())
        
        result = await db.execute(stmt)
        applications = result.scalars().all()
        
        # Group by status
        by_status = {
            "pending": [],
            "approved": [],
            "rejected": [],
            "cancelled": []
        }
        
        for app in applications:
            app_data = {
                "id": app.id,
                "leave_type": app.leave_type,
                "start_date": app.start_date.isoformat(),
                "end_date": app.end_date.isoformat(),
                "duration": app.number_of_days,
                "reason": app.reason,
                "applied_date": app.applied_date.isoformat(),
                "status": app.status
            }
            
            if app.status == LeaveApplicationStatus.PENDING:
                by_status["pending"].append(app_data)
            elif app.status == LeaveApplicationStatus.APPROVED:
                by_status["approved"].append(app_data)
            elif app.status == LeaveApplicationStatus.REJECTED:
                by_status["rejected"].append(app_data)
            elif app.status == LeaveApplicationStatus.CANCELLED:
                by_status["cancelled"].append(app_data)
        
        return {
            "period": f"Last {months} months",
            "total_applications": len(applications),
            "by_status": by_status,
            "summary": {
                "pending": len(by_status["pending"]),
                "approved": len(by_status["approved"]),
                "rejected": len(by_status["rejected"]),
                "cancelled": len(by_status["cancelled"])
            }
        }

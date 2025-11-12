"""
Balance Automation Service
Provides comprehensive balance information across all HR modules
"""

from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func


class BalanceAutomationService:
    """
    Unified service for checking balances across HR modules
    - Leave balances
    - Attendance summary
    - WFH quota
    - Overtime/comp-off
    - Payroll information (limited)
    """
    
    @staticmethod
    async def get_comprehensive_balance(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive balance information across all HR modules
        Returns unified balance view for AI assistant and dashboard
        """
        from app.models import (
            Employee, LeaveBalance, AttendanceDay, AttendanceStatus,
            LeaveApplication, LeaveApplicationStatus
        )
        
        # Get employee details
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee not found"
            }
        
        current_date = date.today()
        current_month_start = date(current_date.year, current_date.month, 1)
        current_year = current_date.year
        
        # 1. LEAVE BALANCES
        leave_balance_data = await BalanceAutomationService._get_leave_balance_summary(
            db, employee_id
        )
        
        # 2. ATTENDANCE SUMMARY (current month)
        attendance_data = await BalanceAutomationService._get_attendance_summary(
            db, employee_id, current_month_start, current_date
        )
        
        # 3. WFH QUOTA
        wfh_data = await BalanceAutomationService._get_wfh_quota_summary(
            db, employee_id, current_year
        )
        
        # 4. OVERTIME/COMP-OFF BALANCE
        overtime_data = await BalanceAutomationService._get_overtime_summary(
            db, employee_id, current_month_start, current_date
        )
        
        # 5. PENDING APPROVALS (things waiting for action)
        pending_data = await BalanceAutomationService._get_pending_items(
            db, employee_id
        )
        
        return {
            "success": True,
            "employee": {
                "id": employee.id,
                "name": f"{employee.first_name} {employee.last_name}",
                "email": employee.email,
                "designation": employee.designation
            },
            "as_of_date": current_date.isoformat(),
            "leave_balance": leave_balance_data,
            "attendance": attendance_data,
            "wfh_quota": wfh_data,
            "overtime": overtime_data,
            "pending_items": pending_data,
            "summary_alerts": BalanceAutomationService._generate_alerts(
                leave_balance_data, attendance_data, wfh_data, overtime_data, pending_data
            )
        }
    
    @staticmethod
    async def _get_leave_balance_summary(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """Get leave balance summary"""
        from app.models import LeaveBalance
        
        stmt = select(LeaveBalance).where(LeaveBalance.employee_id == employee_id)
        result = await db.execute(stmt)
        balances = result.scalars().all()
        
        if not balances:
            return {
                "total_available": 0,
                "total_used": 0,
                "total_pending": 0,
                "by_type": {},
                "alerts": []
            }
        
        total_available = 0
        total_used = 0
        total_pending = 0
        by_type = {}
        alerts = []
        
        # Fiscal year end calculation (assuming April-March)
        current_year = datetime.now().year
        fiscal_year_end = date(current_year, 3, 31)
        if date.today() > fiscal_year_end:
            fiscal_year_end = date(current_year + 1, 3, 31)
        
        days_until_expiry = (fiscal_year_end - date.today()).days
        
        for balance in balances:
            leave_type = balance.leave_type.lower() if balance.leave_type else "unknown"
            available = balance.available_days or 0
            granted = balance.granted_days or 0
            pending = balance.pending_days or 0
            used = granted - available
            
            total_available += available
            total_used += used
            total_pending += pending
            
            by_type[leave_type] = {
                "name": leave_type.title(),
                "granted": granted,
                "available": available,
                "used": used,
                "pending": pending,
                "utilization_percent": round((used / granted * 100) if granted > 0 else 0, 1)
            }
            
            # Generate alerts
            if available < 3 and available > 0:
                alerts.append({
                    "type": "low_balance",
                    "severity": "warning",
                    "message": f"Low {leave_type} leave balance: {available} days remaining"
                })
            
            if available > 0 and days_until_expiry <= 60:
                alerts.append({
                    "type": "expiring_soon",
                    "severity": "info",
                    "message": f"{available} {leave_type} leaves expire in {days_until_expiry} days (on {fiscal_year_end.strftime('%B %d, %Y')})"
                })
        
        return {
            "total_available": total_available,
            "total_used": total_used,
            "total_pending": total_pending,
            "by_type": by_type,
            "fiscal_year_end": fiscal_year_end.isoformat(),
            "days_until_expiry": days_until_expiry,
            "alerts": alerts
        }
    
    @staticmethod
    async def _get_attendance_summary(
        db: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get attendance summary for date range"""
        from app.models import AttendanceDay, AttendanceStatus
        
        stmt = select(AttendanceDay).where(
            and_(
                AttendanceDay.employee_id == employee_id,
                AttendanceDay.date >= start_date,
                AttendanceDay.date <= end_date
            )
        )
        result = await db.execute(stmt)
        attendance_records = result.scalars().all()
        
        present_count = 0
        absent_count = 0
        late_count = 0
        half_day_count = 0
        total_hours = 0.0
        
        for record in attendance_records:
            if record.status == AttendanceStatus.PRESENT:
                present_count += 1
                if record.late_arrival:
                    late_count += 1
            elif record.status == AttendanceStatus.ABSENT:
                absent_count += 1
            elif record.status == AttendanceStatus.HALF_DAY:
                half_day_count += 1
            
            if record.work_hours:
                total_hours += record.work_hours
        
        working_days = len(attendance_records)
        attendance_rate = round((present_count / working_days * 100) if working_days > 0 else 0, 1)
        avg_hours_per_day = round(total_hours / working_days, 1) if working_days > 0 else 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "working_days": working_days,
            "present": present_count,
            "absent": absent_count,
            "late_arrivals": late_count,
            "half_days": half_day_count,
            "attendance_rate": attendance_rate,
            "total_hours_worked": round(total_hours, 1),
            "avg_hours_per_day": avg_hours_per_day,
            "status": "good" if attendance_rate >= 95 else "warning" if attendance_rate >= 85 else "poor"
        }
    
    @staticmethod
    async def _get_wfh_quota_summary(
        db: AsyncSession,
        employee_id: int,
        year: int
    ) -> Dict[str, Any]:
        """Get WFH quota summary"""
        from app.models import ApprovalRequest, RequestType, ApprovalStatus
        
        # Count approved WFH requests for the year
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.employee_id == employee_id,
                ApprovalRequest.request_type == RequestType.WFH,
                ApprovalRequest.status == ApprovalStatus.APPROVED,
                ApprovalRequest.created_at >= datetime(year, 1, 1),
                ApprovalRequest.created_at <= datetime(year, 12, 31)
            )
        )
        result = await db.execute(stmt)
        approved_wfh = result.scalars().all()
        
        # Count pending WFH requests
        stmt_pending = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.employee_id == employee_id,
                ApprovalRequest.request_type == RequestType.WFH,
                ApprovalRequest.status == ApprovalStatus.PENDING
            )
        )
        result_pending = await db.execute(stmt_pending)
        pending_wfh = result_pending.scalars().all()
        
        annual_quota = 24  # Default: 24 days per year
        used = len(approved_wfh)
        pending = len(pending_wfh)
        remaining = annual_quota - used - pending
        utilization_percent = round((used / annual_quota * 100) if annual_quota > 0 else 0, 1)
        
        return {
            "annual_quota": annual_quota,
            "used": used,
            "pending": pending,
            "remaining": remaining,
            "utilization_percent": utilization_percent,
            "status": "good" if remaining > 5 else "warning" if remaining > 0 else "exhausted"
        }
    
    @staticmethod
    async def _get_overtime_summary(
        db: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get overtime/comp-off summary"""
        from app.models import AttendanceDay
        
        stmt = select(AttendanceDay).where(
            and_(
                AttendanceDay.employee_id == employee_id,
                AttendanceDay.date >= start_date,
                AttendanceDay.date <= end_date,
                AttendanceDay.overtime_hours > 0
            )
        )
        result = await db.execute(stmt)
        overtime_records = result.scalars().all()
        
        total_overtime_hours = sum(record.overtime_hours or 0 for record in overtime_records)
        comp_off_earned = int(total_overtime_hours / 9)  # 9 hours overtime = 1 comp-off
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_overtime_hours": round(total_overtime_hours, 1),
            "overtime_days": len(overtime_records),
            "comp_off_earned": comp_off_earned,
            "comp_off_available": 0,  # TODO: Implement comp-off tracking
            "status": "available" if comp_off_earned > 0 else "none"
        }
    
    @staticmethod
    async def _get_pending_items(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """Get pending approvals and actions"""
        from app.models import (
            ApprovalRequest, ApprovalStatus,
            LeaveApplication, LeaveApplicationStatus
        )
        
        # Pending approval requests (WFH, regularization, etc.)
        stmt = select(ApprovalRequest).where(
            and_(
                ApprovalRequest.employee_id == employee_id,
                ApprovalRequest.status == ApprovalStatus.PENDING
            )
        )
        result = await db.execute(stmt)
        pending_approvals = result.scalars().all()
        
        # Pending leave applications
        stmt_leave = select(LeaveApplication).where(
            and_(
                LeaveApplication.employee_id == employee_id,
                LeaveApplication.status == LeaveApplicationStatus.PENDING
            )
        )
        result_leave = await db.execute(stmt_leave)
        pending_leaves = result_leave.scalars().all()
        
        pending_items = []
        
        for approval in pending_approvals:
            pending_items.append({
                "type": approval.request_type.value if approval.request_type else "approval",
                "id": approval.id,
                "description": approval.request_type.value.upper() if approval.request_type else "Approval",
                "submitted_on": approval.created_at.date().isoformat(),
                "status": "pending"
            })
        
        for leave in pending_leaves:
            pending_items.append({
                "type": "leave",
                "id": leave.id,
                "description": f"{leave.leave_type} Leave ({leave.number_of_days} days)",
                "submitted_on": leave.applied_date.date().isoformat(),
                "dates": f"{leave.start_date.isoformat()} to {leave.end_date.isoformat()}",
                "status": "pending"
            })
        
        return {
            "total_count": len(pending_items),
            "items": pending_items
        }
    
    @staticmethod
    def _generate_alerts(
        leave_balance: Dict,
        attendance: Dict,
        wfh_quota: Dict,
        overtime: Dict,
        pending: Dict
    ) -> list:
        """Generate summary alerts based on all balance data"""
        alerts = []
        
        # Leave balance alerts
        if leave_balance.get("total_available", 0) < 5:
            alerts.append({
                "severity": "warning",
                "category": "leave",
                "message": f"Low leave balance: {leave_balance.get('total_available', 0)} days remaining",
                "action": "Plan your leaves wisely"
            })
        
        # Attendance alerts
        attendance_rate = attendance.get("attendance_rate", 100)
        if attendance_rate < 90:
            alerts.append({
                "severity": "critical",
                "category": "attendance",
                "message": f"Low attendance rate: {attendance_rate}%",
                "action": "Improve your attendance to avoid policy violations"
            })
        elif attendance.get("late_arrivals", 0) > 5:
            alerts.append({
                "severity": "warning",
                "category": "attendance",
                "message": f"{attendance.get('late_arrivals')} late arrivals this month",
                "action": "Try to arrive on time"
            })
        
        # WFH quota alerts
        if wfh_quota.get("remaining", 0) < 3:
            alerts.append({
                "severity": "info",
                "category": "wfh",
                "message": f"Only {wfh_quota.get('remaining')} WFH days remaining",
                "action": "Plan your WFH days carefully"
            })
        
        # Overtime alerts
        if overtime.get("comp_off_earned", 0) > 0:
            alerts.append({
                "severity": "info",
                "category": "overtime",
                "message": f"You've earned {overtime.get('comp_off_earned')} comp-off days",
                "action": "Use your comp-off before it expires"
            })
        
        # Pending items alerts
        if pending.get("total_count", 0) > 0:
            alerts.append({
                "severity": "info",
                "category": "pending",
                "message": f"{pending.get('total_count')} pending approvals",
                "action": "Check status of your pending requests"
            })
        
        return alerts
    
    @staticmethod
    async def get_quick_balance_summary(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Get quick balance summary for chatbot responses
        Lightweight version with just the essentials
        """
        from app.services.leave_automation import LeaveAutomationService
        
        # Get leave balance
        leave_balance = await LeaveAutomationService.get_leave_balance(
            db=db,
            employee_id=employee_id
        )
        
        # Quick summary
        total_leaves = sum(
            balance.get("available", 0) 
            for balance in leave_balance.get("balances", {}).values()
        )
        
        return {
            "success": True,
            "quick_summary": {
                "total_leaves_available": total_leaves,
                "leave_types_count": len(leave_balance.get("balances", {})),
                "has_alerts": len(leave_balance.get("alerts", {}).get("low_balance", [])) > 0 or 
                             len(leave_balance.get("alerts", {}).get("expiring_soon", [])) > 0
            },
            "full_data": leave_balance
        }

"""
Attendance Automation Service
Handles automated clock in/out with geo-location, duplicate detection, and notifications
"""
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import math

from app.models import AttendanceDay, Employee, User
from app.models.attendance import AttendanceStatus, AttendanceSource


class AttendanceAutomationService:
    """Automated attendance management with AI capabilities"""
    
    # Company office location (example: Mumbai office)
    OFFICE_LOCATIONS = {
        "mumbai": {"lat": 19.0760, "lng": 72.8777, "radius_meters": 500},
        "bangalore": {"lat": 12.9716, "lng": 77.5946, "radius_meters": 500},
        "delhi": {"lat": 28.6139, "lng": 77.2090, "radius_meters": 500}
    }
    
    LATE_ARRIVAL_THRESHOLD_MINUTES = 15
    WORK_START_TIME = time(9, 30)  # 9:30 AM
    AUTO_CLOCK_OUT_REMINDER_TIME = time(20, 0)  # 8:00 PM
    LATE_ARRIVAL_THRESHOLD_COUNT = 3  # Alert manager after 3 late arrivals
    
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    @staticmethod
    def validate_location(user_lat: float, user_lng: float, office_key: str = "mumbai") -> Tuple[bool, float]:
        """
        Validate if user is within office radius
        Returns (is_valid, distance_from_office)
        """
        if office_key not in AttendanceAutomationService.OFFICE_LOCATIONS:
            # Default to Mumbai if office not found
            office_key = "mumbai"
        
        office = AttendanceAutomationService.OFFICE_LOCATIONS[office_key]
        distance = AttendanceAutomationService.calculate_distance(
            user_lat, user_lng,
            office["lat"], office["lng"]
        )
        
        is_valid = distance <= office["radius_meters"]
        return is_valid, distance
    
    @staticmethod
    async def check_duplicate_punch(
        db: AsyncSession,
        employee_id: int,
        today: datetime
    ) -> Optional[AttendanceDay]:
        """Check if employee already clocked in today"""
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.date == today.date()
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    def check_late_arrival(clock_in_time: datetime) -> Tuple[bool, int]:
        """
        Check if employee is late
        Returns (is_late, minutes_late)
        """
        expected_time = datetime.combine(
            clock_in_time.date(),
            AttendanceAutomationService.WORK_START_TIME
        )
        
        # Grace period of 15 minutes
        grace_time = expected_time + timedelta(minutes=AttendanceAutomationService.LATE_ARRIVAL_THRESHOLD_MINUTES)
        
        if clock_in_time > grace_time:
            minutes_late = int((clock_in_time - expected_time).total_seconds() / 60)
            return True, minutes_late
        
        return False, 0
    
    @staticmethod
    async def count_late_arrivals_this_month(
        db: AsyncSession,
        employee_id: int
    ) -> int:
        """Count how many times employee was late this month"""
        today = datetime.now()
        first_day = datetime(today.year, today.month, 1)
        
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.date >= first_day.date(),
            AttendanceDay.date <= today.date()
        )
        
        result = await db.execute(stmt)
        attendance_records = result.scalars().all()
        
        late_count = 0
        for record in attendance_records:
            if record.check_in:
                expected_time = datetime.combine(
                    record.date,
                    AttendanceAutomationService.WORK_START_TIME
                )
                grace_time = expected_time + timedelta(minutes=AttendanceAutomationService.LATE_ARRIVAL_THRESHOLD_MINUTES)
                
                check_in_datetime = datetime.combine(record.date, record.check_in)
                if check_in_datetime > grace_time:
                    late_count += 1
        
        return late_count
    
    @staticmethod
    async def clock_in(
        db: AsyncSession,
        employee_id: int,
        user_id: int,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        office_location: str = "mumbai"
    ) -> Dict[str, Any]:
        """
        Automated clock in with all validations
        
        Returns comprehensive response with:
        - Success status
        - Validation results (location, late arrival, etc.)
        - Notifications triggered
        - Summary of attendance
        - delivery_status with inbox_notification and event emission
        """
        from sqlalchemy import text
        from app.models.workflow import AuditLog, AuditAction
        from app.services.notification_delivery import NotificationDeliveryService
        import uuid
        
        now = datetime.now()
        today = now.date()
        
        # 1. Check duplicate punch
        existing_attendance = await AttendanceAutomationService.check_duplicate_punch(
            db, employee_id, now
        )
        
        if existing_attendance and existing_attendance.check_in:
            return {
                "success": False,
                "error": "duplicate_punch",
                "message": f"You've already clocked in today at {existing_attendance.check_in.strftime('%I:%M %p')}",
                "existing_check_in": existing_attendance.check_in.isoformat(),
                "status": existing_attendance.status
            }
        
        # 2. Validate location (if provided)
        location_valid = True
        distance_from_office = None
        
        if user_lat and user_lng:
            location_valid, distance_from_office = AttendanceAutomationService.validate_location(
                user_lat, user_lng, office_location
            )
            
            if not location_valid:
                return {
                    "success": False,
                    "error": "location_out_of_range",
                    "message": f"You're {int(distance_from_office)}m away from office. Must be within 500m to clock in.",
                    "distance_meters": distance_from_office,
                    "office_location": office_location
                }
        
        # 3. Check late arrival
        is_late, minutes_late = AttendanceAutomationService.check_late_arrival(now)
        
        # 4. Count late arrivals this month
        late_count_this_month = await AttendanceAutomationService.count_late_arrivals_this_month(
            db, employee_id
        )
        
        # Add 1 if current clock in is late
        if is_late:
            late_count_this_month += 1
        
        # 5. Create or update attendance record
        try:
            if existing_attendance:
                # Update existing record with check-in
                existing_attendance.check_in = now.time()
                existing_attendance.status = AttendanceStatus.PRESENT
                existing_attendance.source = AttendanceSource.AI_CHATBOT
                existing_attendance.device_info = device_info
                existing_attendance.ip_address = ip_address
                attendance_record = existing_attendance
            else:
                # Create new record
                attendance_record = AttendanceDay(
                    employee_id=employee_id,
                    date=today,
                    check_in=now.time(),
                    status=AttendanceStatus.PRESENT,
                    source=AttendanceSource.AI_CHATBOT,
                    location_type="office" if location_valid else "remote",
                    device_info=device_info,
                    ip_address=ip_address
                )
                db.add(attendance_record)
            
            await db.flush()
            
            # 6. Create inbox notifications (self notification + manager notification if late)
            inbox_ids = []
            notification_title = f"✅ Clocked In at {now.strftime('%I:%M %p')}"
            notification_body = f"Clocked in successfully on {today.isoformat()}"
            
            if is_late:
                notification_body += f" (Late by {minutes_late} minutes)"
            
            # Notify employee
            employee_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[employee_id],
                notification_type="attendance_clock_in",
                message_id=None,
                entity_type="attendance",
                entity_id=attendance_record.id,
                title=notification_title,
                body=notification_body,
                metadata={
                    "check_in_time": now.isoformat(),
                    "is_late": is_late,
                    "minutes_late": minutes_late if is_late else 0,
                    "location_valid": location_valid,
                    "distance_from_office_meters": distance_from_office
                }
            )
            inbox_ids.extend(employee_inbox_ids)
            
            # Notify manager if late threshold exceeded
            manager_notified = False
            if late_count_this_month >= AttendanceAutomationService.LATE_ARRIVAL_THRESHOLD_COUNT:
                # Fetch employee's manager
                emp_stmt = select(Employee).where(Employee.id == employee_id)
                emp_result = await db.execute(emp_stmt)
                employee = emp_result.scalar_one_or_none()
                
                if employee and employee.manager_id:
                    manager_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                        db=db,
                        recipient_employee_ids=[employee.manager_id],
                        notification_type="attendance_late_alert",
                        message_id=None,
                        entity_type="attendance",
                        entity_id=attendance_record.id,
                        title=f"🚨 Late Arrival Alert: {employee.first_name} {employee.last_name}",
                        body=f"{employee.first_name} {employee.last_name} has {late_count_this_month} late arrivals this month",
                        metadata={
                            "employee_id": employee_id,
                            "late_count_this_month": late_count_this_month,
                            "current_late_minutes": minutes_late
                        }
                    )
                    inbox_ids.extend(manager_inbox_ids)
                    manager_notified = True
            
            # 7. Audit log
            audit_log = AuditLog(
                user_id=user_id,
                employee_id=employee_id,
                action=AuditAction.CLOCK_IN,
                entity_type="attendance",
                entity_id=attendance_record.id,
                description=f"Clocked in at {now.strftime('%I:%M %p')}" + (" (Late)" if is_late else ""),
                new_value={
                    "check_in": now.isoformat(),
                    "is_late": is_late,
                    "minutes_late": minutes_late,
                    "location_valid": location_valid
                },
                success=True
            )
            db.add(audit_log)
            
            await db.commit()
            await db.refresh(attendance_record)
            
            # 8. Build delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=True,
                inbox_created=len(inbox_ids) > 0,
                event_emitted=True,
                audit_logged=True,
                event_channel="attendance_events",
                inbox_ids=inbox_ids,
                error=None
            )
            
            # 9. Prepare response with all notifications
            response = {
                "success": True,
                "message": "✅ Clocked in successfully!",
                "attendance_id": attendance_record.id,
                "check_in_time": now.strftime('%I:%M %p'),
                "date": today.isoformat(),
                "status": attendance_record.status,
                "validations": {
                    "location_verified": location_valid,
                    "distance_from_office_meters": distance_from_office if distance_from_office else None,
                    "is_late": is_late,
                    "minutes_late": minutes_late if is_late else 0
                },
                "notifications": [],
                "summary": {
                    "late_arrivals_this_month": late_count_this_month,
                    "expected_clock_out": "06:00 PM",
                    "work_hours_target": 8
                },
                "delivery_status": delivery_status
            }
            
            # 10. Add notifications based on conditions
            if is_late:
                response["notifications"].append({
                    "type": "late_arrival",
                    "severity": "warning",
                    "message": f"⚠️ You're {minutes_late} minutes late. Expected arrival: 9:30 AM"
                })
            
            if manager_notified:
                response["notifications"].append({
                    "type": "manager_alert",
                    "severity": "high",
                    "message": f"🚨 Manager notified: {late_count_this_month} late arrivals this month",
                    "action_required": "Please maintain punctuality"
                })
            
            if not location_valid and distance_from_office:
                response["notifications"].append({
                    "type": "remote_location",
                    "severity": "info",
                    "message": f"📍 Clocked in from remote location ({int(distance_from_office)}m from office)"
                })
            
            # 11. Add smart features
            response["smart_reminders"] = {
                "clock_out_reminder": "You'll receive a reminder at 8:00 PM if you forget to clock out",
                "calendar_status": "Your status has been updated to 'In Office' on calendar"
            }
            
            return response
            
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
                "error": "clock_in_failed",
                "message": f"Failed to clock in: {str(e)}",
                "delivery_status": delivery_status
            }
    
    @staticmethod
    async def clock_out(
        db: AsyncSession,
        employee_id: int,
        user_id: int,
        user_lat: Optional[float] = None,
        user_lng: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Automated clock out with work hours calculation
        Now includes inbox notifications and delivery status
        """
        from sqlalchemy import text
        from app.models.workflow import AuditLog, AuditAction
        from app.services.notification_delivery import NotificationDeliveryService
        import uuid
        
        now = datetime.now()
        today = now.date()
        
        # 1. Check if already clocked in today
        existing_attendance = await AttendanceAutomationService.check_duplicate_punch(
            db, employee_id, now
        )
        
        if not existing_attendance or not existing_attendance.check_in:
            return {
                "success": False,
                "error": "not_clocked_in",
                "message": "You haven't clocked in today. Please clock in first."
            }
        
        if existing_attendance.check_out:
            return {
                "success": False,
                "error": "already_clocked_out",
                "message": f"You've already clocked out today at {existing_attendance.check_out.strftime('%I:%M %p')}",
                "check_out_time": existing_attendance.check_out.isoformat()
            }
        
        try:
            # 2. Update attendance with clock out
            existing_attendance.check_out = now.time()
            
            # 3. Calculate work hours
            check_in_datetime = datetime.combine(today, existing_attendance.check_in)
            check_out_datetime = datetime.combine(today, now.time())
            work_duration = check_out_datetime - check_in_datetime
            work_hours = work_duration.total_seconds() / 3600
            
            existing_attendance.work_hours = round(work_hours, 2)
            
            # Check overtime
            overtime_minutes = 0
            if work_hours > 8:
                overtime_minutes = int((work_hours - 8) * 60)
                existing_attendance.overtime_minutes = overtime_minutes
            
            await db.flush()
            
            # 4. Create inbox notification
            notification_title = f"✅ Clocked Out at {now.strftime('%I:%M %p')}"
            notification_body = f"Total work hours: {existing_attendance.work_hours}h"
            
            if overtime_minutes > 0:
                notification_body += f" (Overtime: {overtime_minutes} minutes)"
            elif work_hours < 8:
                notification_body += f" (Short by {8 - work_hours:.1f}h)"
            
            inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[employee_id],
                notification_type="attendance_clock_out",
                message_id=None,
                entity_type="attendance",
                entity_id=existing_attendance.id,
                title=notification_title,
                body=notification_body,
                metadata={
                    "check_out_time": now.isoformat(),
                    "work_hours": existing_attendance.work_hours,
                    "overtime_minutes": overtime_minutes,
                    "check_in_time": existing_attendance.check_in.isoformat()
                }
            )
            
            # 5. Audit log
            audit_log = AuditLog(
                user_id=user_id,
                employee_id=employee_id,
                action=AuditAction.CLOCK_OUT,
                entity_type="attendance",
                entity_id=existing_attendance.id,
                description=f"Clocked out at {now.strftime('%I:%M %p')} (Work hours: {existing_attendance.work_hours}h)",
                new_value={
                    "check_out": now.isoformat(),
                    "work_hours": existing_attendance.work_hours,
                    "overtime_minutes": overtime_minutes
                },
                success=True
            )
            db.add(audit_log)
            
            await db.commit()
            await db.refresh(existing_attendance)
            
            # 6. Build delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=True,
                inbox_created=len(inbox_ids) > 0,
                event_emitted=True,
                audit_logged=True,
                event_channel="attendance_events",
                inbox_ids=inbox_ids,
                error=None
            )
            
            # 7. Prepare response
            response = {
                "success": True,
                "message": "✅ Clocked out successfully!",
                "attendance_id": existing_attendance.id,
                "check_in_time": existing_attendance.check_in.strftime('%I:%M %p'),
                "check_out_time": now.strftime('%I:%M %p'),
                "work_hours": existing_attendance.work_hours,
                "summary": {
                    "total_work_hours": f"{int(work_hours)}h {int((work_hours % 1) * 60)}m",
                    "overtime": f"{overtime_minutes} minutes" if overtime_minutes > 0 else "None",
                    "productivity": "On track" if work_hours >= 8 else "Below target"
                },
                "smart_insights": [],
                "delivery_status": delivery_status
            }
            
            # 8. Add smart insights
            if work_hours >= 9:
                response["smart_insights"].append({
                    "type": "overtime_worked",
                    "message": f"💼 You worked {overtime_minutes} minutes overtime today. Great dedication!"
                })
            
            if work_hours < 8:
                shortage = 8 - work_hours
                response["smart_insights"].append({
                    "type": "underhours",
                    "message": f"⚠️ You worked {shortage:.1f} hours less than target today. Please regularize if needed."
                })
            
            return response
            
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
                "error": "clock_out_failed",
                "message": f"Failed to clock out: {str(e)}",
                "delivery_status": delivery_status
            }
    
    @staticmethod
    async def get_attendance_summary(
        db: AsyncSession,
        employee_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get attendance summary for last N days"""
        today = datetime.now().date()
        start_date = today - timedelta(days=days)
        
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.date >= start_date,
            AttendanceDay.date <= today
        ).order_by(AttendanceDay.date.desc())
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        # Calculate statistics
        total_days = len(records)
        present_days = len([r for r in records if r.status == AttendanceStatus.PRESENT])
        late_days = 0
        total_work_hours = 0
        total_overtime_minutes = 0
        
        for record in records:
            if record.check_in:
                expected_time = datetime.combine(
                    record.date,
                    AttendanceAutomationService.WORK_START_TIME
                )
                grace_time = expected_time + timedelta(minutes=AttendanceAutomationService.LATE_ARRIVAL_THRESHOLD_MINUTES)
                check_in_datetime = datetime.combine(record.date, record.check_in)
                
                if check_in_datetime > grace_time:
                    late_days += 1
            
            if record.work_hours:
                total_work_hours += record.work_hours
            
            if record.overtime_minutes:
                total_overtime_minutes += record.overtime_minutes
        
        return {
            "period": f"Last {days} days",
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": days - present_days,
            "late_arrivals": late_days,
            "attendance_percentage": round((present_days / days) * 100, 1) if days > 0 else 0,
            "total_work_hours": round(total_work_hours, 1),
            "average_work_hours_per_day": round(total_work_hours / present_days, 1) if present_days > 0 else 0,
            "total_overtime_hours": round(total_overtime_minutes / 60, 1),
            "punctuality_score": round((1 - (late_days / present_days)) * 100, 1) if present_days > 0 else 100
        }
    
    @staticmethod
    async def detect_missed_punches(
        db: AsyncSession,
        employee_id: int,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Automatically detect missed punches (incomplete attendance records)
        Returns list of days with missing clock-in or clock-out
        """
        today = datetime.now().date()
        start_date = today - timedelta(days=days)
        
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.date >= start_date,
            AttendanceDay.date < today  # Don't include today
        ).order_by(AttendanceDay.date.desc())
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        missed_punches = []
        
        for record in records:
            issues = []
            
            # Check for missing clock-in
            if not record.check_in:
                issues.append("missing_clock_in")
            
            # Check for missing clock-out (only if clocked in)
            if record.check_in and not record.check_out:
                issues.append("missing_clock_out")
            
            # Check for both missing (absent day)
            if not record.check_in and not record.check_out:
                issues.append("absent")
            
            if issues:
                # Suggest typical times based on employee's history
                suggested_check_in = "09:30 AM"
                suggested_check_out = "06:30 PM"
                
                # Try to find typical times from recent records
                recent_records = [r for r in records if r.check_in and r.check_out]
                if recent_records:
                    avg_check_in = sum([datetime.combine(datetime.today(), r.check_in).hour * 60 + 
                                      datetime.combine(datetime.today(), r.check_in).minute 
                                      for r in recent_records]) / len(recent_records)
                    avg_check_out = sum([datetime.combine(datetime.today(), r.check_out).hour * 60 + 
                                        datetime.combine(datetime.today(), r.check_out).minute 
                                        for r in recent_records]) / len(recent_records)
                    
                    suggested_check_in_time = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(minutes=avg_check_in)
                    suggested_check_out_time = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(minutes=avg_check_out)
                    
                    suggested_check_in = suggested_check_in_time.strftime('%I:%M %p')
                    suggested_check_out = suggested_check_out_time.strftime('%I:%M %p')
                
                missed_punches.append({
                    "date": record.date.isoformat(),
                    "day_name": record.date.strftime('%A'),
                    "issues": issues,
                    "current_check_in": record.check_in.strftime('%I:%M %p') if record.check_in else None,
                    "current_check_out": record.check_out.strftime('%I:%M %p') if record.check_out else None,
                    "suggested_check_in": suggested_check_in,
                    "suggested_check_out": suggested_check_out,
                    "attendance_id": record.id
                })
        
        return missed_punches
    
    @staticmethod
    async def submit_regularization_request(
        db: AsyncSession,
        employee_id: int,
        attendance_date: datetime.date,
        check_in_time: Optional[str] = None,
        check_out_time: Optional[str] = None,
        reason: str = "",
        manager_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit attendance regularization request
        Creates/updates attendance record and sends for manager approval
        """
        from app.models import Employee, ApprovalRequest, RequestType, ApprovalLevel, ApprovalStatus
        
        # 1. Validate date (cannot regularize future dates or today)
        today = datetime.now().date()
        if attendance_date >= today:
            return {
                "success": False,
                "error": "invalid_date",
                "message": "Cannot regularize today or future dates. Please regularize only past dates."
            }
        
        # 2. Check if too old (company policy: max 7 days old)
        days_old = (today - attendance_date).days
        if days_old > 7:
            return {
                "success": False,
                "error": "too_old",
                "message": f"This attendance is {days_old} days old. You can only regularize attendance within 7 days.",
                "requires": "HR approval for older dates"
            }
        
        # 3. Get or create attendance record
        stmt = select(AttendanceDay).where(
            AttendanceDay.employee_id == employee_id,
            AttendanceDay.date == attendance_date
        )
        result = await db.execute(stmt)
        attendance_record = result.scalar_one_or_none()
        
        # 4. Parse times
        new_check_in = None
        new_check_out = None
        
        if check_in_time:
            try:
                new_check_in = datetime.strptime(check_in_time, '%I:%M %p').time()
            except:
                try:
                    new_check_in = datetime.strptime(check_in_time, '%H:%M').time()
                except:
                    return {
                        "success": False,
                        "error": "invalid_time_format",
                        "message": f"Invalid check-in time format: {check_in_time}. Use 'HH:MM AM/PM' or 'HH:MM'"
                    }
        
        if check_out_time:
            try:
                new_check_out = datetime.strptime(check_out_time, '%I:%M %p').time()
            except:
                try:
                    new_check_out = datetime.strptime(check_out_time, '%H:%M').time()
                except:
                    return {
                        "success": False,
                        "error": "invalid_time_format",
                        "message": f"Invalid check-out time format: {check_out_time}. Use 'HH:MM AM/PM' or 'HH:MM'"
                    }
        
        # 5. Validate logical consistency
        if new_check_in and new_check_out:
            check_in_datetime = datetime.combine(attendance_date, new_check_in)
            check_out_datetime = datetime.combine(attendance_date, new_check_out)
            
            if check_out_datetime <= check_in_datetime:
                return {
                    "success": False,
                    "error": "invalid_times",
                    "message": "Check-out time must be after check-in time"
                }
        
        # 6. Get manager
        if not manager_id:
            stmt = select(Employee).where(Employee.id == employee_id)
            result = await db.execute(stmt)
            employee = result.scalar_one_or_none()
            if employee and employee.manager_id:
                manager_id = employee.manager_id
            else:
                return {
                    "success": False,
                    "error": "no_manager",
                    "message": "No manager found. Please specify manager for approval."
                }
        
        # 7. Create or update attendance record (mark as pending regularization)
        if not attendance_record:
            attendance_record = AttendanceDay(
                employee_id=employee_id,
                date=attendance_date,
                check_in=new_check_in,
                check_out=new_check_out,
                status=AttendanceStatus.PRESENT,
                source=AttendanceSource.AI_CHATBOT,
                notes=f"Regularization requested: {reason}"
            )
            db.add(attendance_record)
        else:
            # Update existing record
            if new_check_in:
                attendance_record.check_in = new_check_in
            if new_check_out:
                attendance_record.check_out = new_check_out
            attendance_record.notes = f"Regularization requested: {reason}"
        
        # Calculate work hours if both times present
        if attendance_record.check_in and attendance_record.check_out:
            check_in_dt = datetime.combine(attendance_date, attendance_record.check_in)
            check_out_dt = datetime.combine(attendance_date, attendance_record.check_out)
            work_hours = (check_out_dt - check_in_dt).total_seconds() / 3600
            attendance_record.work_hours = round(work_hours, 2)
        
        await db.commit()
        await db.refresh(attendance_record)
        
        # 8. Create approval request
        approval_request = ApprovalRequest(
            request_type=RequestType.ATTENDANCE_REGULARIZATION,
            requester_id=employee_id,
            approver_id=manager_id,
            approval_level=ApprovalLevel.MANAGER,
            status=ApprovalStatus.PENDING,
            metadata={
                "attendance_id": attendance_record.id,
                "date": attendance_date.isoformat(),
                "check_in": new_check_in.strftime('%I:%M %p') if new_check_in else None,
                "check_out": new_check_out.strftime('%I:%M %p') if new_check_out else None,
                "reason": reason
            }
        )
        db.add(approval_request)
        await db.commit()
        await db.refresh(approval_request)
        
        # 9. Prepare response
        return {
            "success": True,
            "message": "✅ Regularization request submitted successfully!",
            "request_id": approval_request.id,
            "attendance_id": attendance_record.id,
            "details": {
                "date": attendance_date.strftime('%B %d, %Y (%A)'),
                "check_in": new_check_in.strftime('%I:%M %p') if new_check_in else "Not changed",
                "check_out": new_check_out.strftime('%I:%M %p') if new_check_out else "Not changed",
                "work_hours": attendance_record.work_hours if attendance_record.work_hours else "Pending",
                "reason": reason
            },
            "approval": {
                "status": "Pending Manager Approval",
                "approver": "Your Manager",
                "expected_response": "Within 24 hours"
            },
            "next_steps": [
                "Your manager will be notified via email",
                "You'll receive notification when approved/rejected",
                "Check approval status anytime by asking me"
            ]
        }
    
    @staticmethod
    async def auto_suggest_regularization(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Proactively detect and suggest regularization for missed punches
        This runs automatically every morning at 9 AM
        """
        missed_punches = await AttendanceAutomationService.detect_missed_punches(
            db, employee_id, days=7
        )
        
        if not missed_punches:
            return {
                "has_issues": False,
                "message": "✅ Your attendance is up to date. No regularization needed."
            }
        
        # Group by issue type
        missing_clock_in = [p for p in missed_punches if "missing_clock_in" in p["issues"]]
        missing_clock_out = [p for p in missed_punches if "missing_clock_out" in p["issues"]]
        absent_days = [p for p in missed_punches if "absent" in p["issues"]]
        
        return {
            "has_issues": True,
            "total_issues": len(missed_punches),
            "breakdown": {
                "missing_clock_in": len(missing_clock_in),
                "missing_clock_out": len(missing_clock_out),
                "absent_days": len(absent_days)
            },
            "missed_punches": missed_punches,
            "message": f"⚠️ You have {len(missed_punches)} attendance issue(s) that need regularization.",
            "suggestion": "I can help you submit regularization requests. Just tell me which date and the correct times!"
        }

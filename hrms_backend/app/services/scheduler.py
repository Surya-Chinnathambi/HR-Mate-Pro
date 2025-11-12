"""
APScheduler Background Jobs Service

This module handles all scheduled background tasks for the HRMS system:
1. Escalation job - Check and escalate overdue approvals
2. Reminder job - Send reminders for overdue tasks
3. Workload sync job - Recalculate employee workloads
4. Analytics job - Generate daily reports
5. Cleanup job - Archive old records
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, or_, func
from typing import List, Dict, Any
import logging

from app.database import sync_engine
from app.models.workflow import ApprovalRequest, ApprovalStep, WorkAssignment
from app.models.user import Employee
from app.models.extras import Notification
from app.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()


# ============================================================================
# JOB 1: ESCALATION CHECKER (Every 1 hour)
# ============================================================================

async def check_and_escalate_approvals():
    """
    Check for pending approval steps that have exceeded their SLA.
    Escalate to next level or mark as overdue.
    Runs every hour.
    """
    logger.info("🔍 Starting escalation check job...")
    
    with Session(sync_engine) as db:
        try:
            # Initialize notification service with session
            notification_service = NotificationService(db)
            
            # Get current time
            now = datetime.utcnow()
            
            # Find pending approval steps that have exceeded SLA
            # SLA is typically defined in approval chain (default 24-48 hours)
            pending_steps = db.execute(
                select(ApprovalStep)
                .where(
                    and_(
                        ApprovalStep.status == 'pending',
                        ApprovalStep.assigned_at != None,
                        ApprovalStep.assigned_at < now - timedelta(hours=24)  # 24-hour SLA
                    )
                )
            ).scalars().all()
            
            escalated_count = 0
            
            for step in pending_steps:
                # Calculate how long it's been pending
                time_pending = now - step.assigned_at
                hours_pending = time_pending.total_seconds() / 3600
                
                # Get the approval request
                approval_request = db.execute(
                    select(ApprovalRequest)
                    .where(ApprovalRequest.request_id == step.request_id)
                ).scalar_one_or_none()
                
                if not approval_request:
                    continue
                
                # Check if we should escalate based on SLA hours
                sla_hours = step.sla_hours if step.sla_hours else 24
                
                if hours_pending >= sla_hours:
                    # Mark step as escalated
                    step.status = 'escalated'
                    step.escalated_at = now
                    db.add(step)
                    
                    # Check if there's a next level to escalate to
                    next_level_step = db.execute(
                        select(ApprovalStep)
                        .where(
                            and_(
                                ApprovalStep.request_id == step.request_id,
                                ApprovalStep.level == step.level + 1,
                                ApprovalStep.status == 'pending'
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if next_level_step:
                        # Escalate to next level
                        next_level_step.assigned_at = now
                        db.add(next_level_step)
                        
                        # Notify next approver
                        await notification_service.send_notification(
                            user_id=next_level_step.approver_id,
                            title=f"Escalated Approval: {approval_request.request_type}",
                            message=f"Request #{approval_request.request_id} has been escalated to you for approval. Previous approver: {step.approver_id}",
                            notification_type="approval_escalation",
                            priority="urgent",
                            related_id=approval_request.request_id
                        )
                        
                        logger.info(f"✅ Escalated approval {approval_request.request_id} from level {step.level} to {next_level_step.level}")
                    else:
                        # No next level - notify requester and manager
                        await notification_service.send_notification(
                            user_id=approval_request.requester_id,
                            title="Approval Overdue",
                            message=f"Your {approval_request.request_type} request #{approval_request.request_id} has exceeded the SLA and is marked as overdue.",
                            notification_type="approval_overdue",
                            priority="high",
                            related_id=approval_request.request_id
                        )
                        
                        logger.warning(f"⚠️ Approval {approval_request.request_id} has no next level to escalate to")
                    
                    escalated_count += 1
            
            # Commit all changes
            db.commit()
            
            logger.info(f"✅ Escalation check completed: {escalated_count} approvals escalated")
            
        except Exception as e:
            logger.error(f"❌ Error in escalation check job: {str(e)}")
            db.rollback()
            raise


# ============================================================================
# JOB 2: TASK REMINDER (Daily at 9:00 AM)
# ============================================================================

async def send_task_reminders():
    """
    Send reminders for overdue and approaching due date tasks.
    Runs daily at 9:00 AM.
    """
    logger.info("📧 Starting task reminder job...")
    
    with Session(sync_engine) as db:
        try:
            # Initialize notification service with session
            notification_service = NotificationService(db)
            
            now = datetime.utcnow()
            today = now.date()
            tomorrow = today + timedelta(days=1)
            
            # Find overdue tasks (due date passed, status not completed)
            overdue_tasks = db.execute(
                select(WorkAssignment)
                .where(
                    and_(
                        WorkAssignment.due_date < now,
                        WorkAssignment.status.in_(['NOT_STARTED', 'IN_PROGRESS', 'BLOCKED'])
                    )
                )
            ).scalars().all()
            
            # Find tasks due today or tomorrow
            upcoming_tasks = db.execute(
                select(WorkAssignment)
                .where(
                    and_(
                        WorkAssignment.due_date >= now,
                        WorkAssignment.due_date <= now + timedelta(days=2),
                        WorkAssignment.status.in_(['NOT_STARTED', 'IN_PROGRESS'])
                    )
                )
            ).scalars().all()
            
            overdue_count = 0
            upcoming_count = 0
            
            # Send reminders for overdue tasks
            for task in overdue_tasks:
                days_overdue = (now.date() - task.due_date.date()).days
                
                # Notify assignee
                await notification_service.send_notification(
                    user_id=task.assignee_id,
                    title="⚠️ Overdue Task Reminder",
                    message=f"Task '{task.title}' is {days_overdue} day(s) overdue. Priority: {task.priority}",
                    notification_type="task_reminder",
                    priority="urgent" if days_overdue > 3 else "high",
                    related_id=task.task_id,
                    channels=['in_app', 'email']  # Send via multiple channels
                )
                
                # Also notify assigner (manager)
                if task.assigner_id != task.assignee_id:
                    await notification_service.send_notification(
                        user_id=task.assigner_id,
                        title="Team Member Has Overdue Task",
                        message=f"Task '{task.title}' assigned to employee #{task.assignee_id} is {days_overdue} day(s) overdue.",
                        notification_type="task_alert",
                        priority="medium",
                        related_id=task.task_id
                    )
                
                overdue_count += 1
            
            # Send reminders for upcoming tasks
            for task in upcoming_tasks:
                days_until_due = (task.due_date.date() - now.date()).days
                
                await notification_service.send_notification(
                    user_id=task.assignee_id,
                    title="📅 Task Due Soon",
                    message=f"Task '{task.title}' is due in {days_until_due} day(s). Progress: {task.progress_percentage}%",
                    notification_type="task_reminder",
                    priority="medium",
                    related_id=task.task_id,
                    channels=['in_app']
                )
                
                upcoming_count += 1
            
            logger.info(f"✅ Task reminders sent: {overdue_count} overdue, {upcoming_count} upcoming")
            
        except Exception as e:
            logger.error(f"❌ Error in task reminder job: {str(e)}")
            raise


# ============================================================================
# JOB 3: WORKLOAD SYNC (Every 6 hours)
# ============================================================================

async def sync_employee_workload():
    """
    Recalculate and update employee workload based on active tasks.
    Detect overloaded employees and alert managers.
    Runs every 6 hours.
    """
    logger.info("⚖️ Starting workload sync job...")
    
    with Session(sync_engine) as db:
        try:
            # Initialize notification service with session
            notification_service = NotificationService(db)
            
            # Get all employees
            employees = db.execute(select(Employee)).scalars().all()
            
            updated_count = 0
            overloaded_employees = []
            
            for employee in employees:
                # Calculate current workload from active tasks
                active_tasks = db.execute(
                    select(WorkAssignment)
                    .where(
                        and_(
                            WorkAssignment.assignee_id == employee.employee_id,
                            WorkAssignment.status.in_(['NOT_STARTED', 'IN_PROGRESS'])
                        )
                    )
                ).scalars().all()
                
                # Sum up estimated hours from active tasks
                total_hours = sum(task.estimated_hours for task in active_tasks if task.estimated_hours)
                
                # Calculate utilization percentage (assuming 40-hour work week)
                weekly_capacity = employee.weekly_capacity if employee.weekly_capacity else 40.0
                utilization = (total_hours / weekly_capacity) * 100 if weekly_capacity > 0 else 0
                
                # Update employee record
                old_workload = employee.current_workload_hours
                employee.current_workload_hours = total_hours
                employee.utilization_percent = utilization
                db.add(employee)
                
                # Check if employee is overloaded (>80% utilization)
                if utilization > 80:
                    overloaded_employees.append({
                        'employee_id': employee.employee_id,
                        'name': employee.full_name,
                        'utilization': utilization,
                        'active_tasks': len(active_tasks)
                    })
                
                if abs(total_hours - old_workload) > 0.1:  # Only log if changed
                    updated_count += 1
            
            # Commit all workload updates
            db.commit()
            
            # Alert managers about overloaded employees
            if overloaded_employees:
                # Group by manager
                manager_alerts: Dict[int, List[Dict]] = {}
                
                for emp_data in overloaded_employees:
                    employee = db.execute(
                        select(Employee)
                        .where(Employee.employee_id == emp_data['employee_id'])
                    ).scalar_one()
                    
                    manager_id = employee.manager_id
                    if manager_id:
                        if manager_id not in manager_alerts:
                            manager_alerts[manager_id] = []
                        manager_alerts[manager_id].append(emp_data)
                
                # Send alerts to managers
                for manager_id, employees_list in manager_alerts.items():
                    employee_names = ', '.join([e['name'] for e in employees_list[:3]])
                    if len(employees_list) > 3:
                        employee_names += f" and {len(employees_list) - 3} more"
                    
                    await notification_service.send_notification(
                        user_id=manager_id,
                        title="⚠️ Team Members Overloaded",
                        message=f"The following team members are at >80% capacity: {employee_names}",
                        notification_type="workload_alert",
                        priority="high",
                        channels=['in_app', 'email']
                    )
                    
                    # Also broadcast via WebSocket for real-time updates
                    try:
                        from app.api.websocket import broadcast_workload_alert
                        await broadcast_workload_alert(manager_id, {
                            'overloaded_employees': employees_list,
                            'message': f"{len(employees_list)} team member(s) at >80% capacity"
                        })
                    except ImportError:
                        pass  # WebSocket module not available
            
            logger.info(f"✅ Workload sync completed: {updated_count} employees updated, {len(overloaded_employees)} overloaded")
            
        except Exception as e:
            logger.error(f"❌ Error in workload sync job: {str(e)}")
            db.rollback()
            raise


# ============================================================================
# JOB 4: ANALYTICS GENERATOR (Daily at 11:00 PM)
# ============================================================================

async def generate_daily_analytics():
    """
    Generate daily analytics reports and metrics.
    Runs daily at 11:00 PM.
    """
    logger.info("📊 Starting analytics generation job...")
    
    with Session(sync_engine) as db:
        try:
            # Initialize notification service with session
            notification_service = NotificationService(db)
            
            now = datetime.utcnow()
            today_start = datetime.combine(now.date(), datetime.min.time())
            today_end = datetime.combine(now.date(), datetime.max.time())
            
            # ========== APPROVAL METRICS ==========
            
            # Count approvals processed today
            approvals_today = db.execute(
                select(func.count(ApprovalStep.step_id))
                .where(
                    and_(
                        ApprovalStep.reviewed_at >= today_start,
                        ApprovalStep.reviewed_at <= today_end
                    )
                )
            ).scalar()
            
            # Calculate average approval time
            avg_approval_time = db.execute(
                select(func.avg(
                    func.extract('epoch', ApprovalStep.reviewed_at - ApprovalStep.assigned_at)
                ))
                .where(
                    and_(
                        ApprovalStep.reviewed_at >= today_start,
                        ApprovalStep.reviewed_at <= today_end,
                        ApprovalStep.status.in_(['approved', 'rejected'])
                    )
                )
            ).scalar()
            
            # Count by status
            approved_today = db.execute(
                select(func.count(ApprovalStep.step_id))
                .where(
                    and_(
                        ApprovalStep.reviewed_at >= today_start,
                        ApprovalStep.reviewed_at <= today_end,
                        ApprovalStep.status == 'approved'
                    )
                )
            ).scalar()
            
            rejected_today = db.execute(
                select(func.count(ApprovalStep.step_id))
                .where(
                    and_(
                        ApprovalStep.reviewed_at >= today_start,
                        ApprovalStep.reviewed_at <= today_end,
                        ApprovalStep.status == 'rejected'
                    )
                )
            ).scalar()
            
            approval_rate = (approved_today / approvals_today * 100) if approvals_today > 0 else 0
            
            # ========== TASK METRICS ==========
            
            # Tasks completed today
            tasks_completed_today = db.execute(
                select(func.count(WorkAssignment.task_id))
                .where(
                    and_(
                        WorkAssignment.status == 'COMPLETED',
                        WorkAssignment.updated_at >= today_start,
                        WorkAssignment.updated_at <= today_end
                    )
                )
            ).scalar()
            
            # Tasks created today
            tasks_created_today = db.execute(
                select(func.count(WorkAssignment.task_id))
                .where(
                    and_(
                        WorkAssignment.created_at >= today_start,
                        WorkAssignment.created_at <= today_end
                    )
                )
            ).scalar()
            
            # Overdue tasks
            overdue_tasks = db.execute(
                select(func.count(WorkAssignment.task_id))
                .where(
                    and_(
                        WorkAssignment.due_date < now,
                        WorkAssignment.status.in_(['NOT_STARTED', 'IN_PROGRESS'])
                    )
                )
            ).scalar()
            
            # Average task completion time
            avg_task_completion_time = db.execute(
                select(func.avg(
                    func.extract('epoch', WorkAssignment.updated_at - WorkAssignment.created_at)
                ))
                .where(
                    and_(
                        WorkAssignment.status == 'COMPLETED',
                        WorkAssignment.updated_at >= today_start,
                        WorkAssignment.updated_at <= today_end
                    )
                )
            ).scalar()
            
            # ========== WORKLOAD METRICS ==========
            
            # Average team utilization
            avg_utilization = db.execute(
                select(func.avg(Employee.utilization_percent))
                .where(Employee.utilization_percent != None)
            ).scalar()
            
            # Employees at capacity
            at_capacity_count = db.execute(
                select(func.count(Employee.employee_id))
                .where(Employee.utilization_percent > 80)
            ).scalar()
            
            # Build analytics report
            analytics_report = {
                'date': today_start.date().isoformat(),
                'approvals': {
                    'total_processed': approvals_today or 0,
                    'approved': approved_today or 0,
                    'rejected': rejected_today or 0,
                    'approval_rate': round(approval_rate, 2),
                    'avg_approval_time_hours': round(avg_approval_time / 3600, 2) if avg_approval_time else 0
                },
                'tasks': {
                    'created': tasks_created_today or 0,
                    'completed': tasks_completed_today or 0,
                    'overdue': overdue_tasks or 0,
                    'avg_completion_time_hours': round(avg_task_completion_time / 3600, 2) if avg_task_completion_time else 0
                },
                'workload': {
                    'avg_utilization': round(avg_utilization, 2) if avg_utilization else 0,
                    'at_capacity_count': at_capacity_count or 0
                }
            }
            
            # Log the report
            logger.info(f"📊 Daily Analytics Report for {today_start.date()}:")
            logger.info(f"   Approvals: {approvals_today} processed, {approval_rate:.1f}% approved")
            logger.info(f"   Tasks: {tasks_completed_today} completed, {overdue_tasks} overdue")
            logger.info(f"   Workload: {avg_utilization:.1f}% avg utilization, {at_capacity_count} at capacity")
            
            # Send summary to all managers
            managers = db.execute(
                select(Employee)
                .where(Employee.role == 'Manager')
            ).scalars().all()
            
            for manager in managers:
                await notification_service.send_notification(
                    user_id=manager.employee_id,
                    title="📊 Daily Analytics Summary",
                    message=f"Approvals: {approvals_today} | Tasks: {tasks_completed_today} completed | {overdue_tasks} overdue | Avg utilization: {avg_utilization:.1f}%",
                    notification_type="analytics_report",
                    priority="low",
                    channels=['in_app']
                )
            
            logger.info(f"✅ Analytics generation completed, summary sent to {len(managers)} managers")
            
            # TODO: Store analytics in a dedicated analytics table for historical tracking
            
        except Exception as e:
            logger.error(f"❌ Error in analytics generation job: {str(e)}")
            raise


# ============================================================================
# JOB 5: CLEANUP (Weekly on Sunday at 2:00 AM)
# ============================================================================

async def cleanup_old_records():
    """
    Archive and cleanup old records to maintain database performance.
    Runs weekly on Sunday at 2:00 AM.
    """
    logger.info("🧹 Starting cleanup job...")
    
    with Session(sync_engine) as db:
        try:
            now = datetime.utcnow()
            
            # ========== CLEANUP OLD NOTIFICATIONS ==========
            # Delete read notifications older than 30 days
            old_notifications_cutoff = now - timedelta(days=30)
            
            deleted_notifications = db.execute(
                select(func.count(Notification.notification_id))
                .where(
                    and_(
                        Notification.is_read == True,
                        Notification.created_at < old_notifications_cutoff
                    )
                )
            ).scalar()
            
            db.execute(
                Notification.__table__.delete().where(
                    and_(
                        Notification.is_read == True,
                        Notification.created_at < old_notifications_cutoff
                    )
                )
            )
            
            # ========== ARCHIVE COMPLETED TASKS ==========
            # Archive tasks completed more than 90 days ago
            # (In production, this would move to an archive table)
            old_tasks_cutoff = now - timedelta(days=90)
            
            archived_tasks = db.execute(
                select(func.count(WorkAssignment.task_id))
                .where(
                    and_(
                        WorkAssignment.status == 'COMPLETED',
                        WorkAssignment.updated_at < old_tasks_cutoff
                    )
                )
            ).scalar()
            
            # For now, just count them. In production, move to archive table
            # db.execute(
            #     WorkAssignment.__table__.delete().where(
            #         and_(
            #             WorkAssignment.status == 'COMPLETED',
            #             WorkAssignment.updated_at < old_tasks_cutoff
            #         )
            #     )
            # )
            
            # ========== ARCHIVE OLD APPROVAL REQUESTS ==========
            # Archive completed/rejected approval requests older than 1 year
            old_approvals_cutoff = now - timedelta(days=365)
            
            archived_approvals = db.execute(
                select(func.count(ApprovalRequest.request_id))
                .where(
                    and_(
                        ApprovalRequest.status.in_(['approved', 'rejected', 'cancelled']),
                        ApprovalRequest.created_at < old_approvals_cutoff
                    )
                )
            ).scalar()
            
            # For now, just count them. In production, move to archive table
            
            # ========== VACUUM DATABASE (if PostgreSQL) ==========
            # This would be done by a separate maintenance script
            # db.execute("VACUUM ANALYZE")
            
            # Commit cleanup
            db.commit()
            
            logger.info(f"✅ Cleanup completed:")
            logger.info(f"   - {deleted_notifications} old notifications deleted")
            logger.info(f"   - {archived_tasks} completed tasks marked for archival")
            logger.info(f"   - {archived_approvals} old approvals marked for archival")
            
        except Exception as e:
            logger.error(f"❌ Error in cleanup job: {str(e)}")
            db.rollback()
            raise


# ============================================================================
# SCHEDULER INITIALIZATION
# ============================================================================

def start_scheduler():
    """
    Initialize and start the APScheduler with all jobs.
    """
    logger.info("🚀 Initializing APScheduler...")
    
    # Job 1: Escalation checker - Every 1 hour
    scheduler.add_job(
        check_and_escalate_approvals,
        trigger=IntervalTrigger(hours=1),
        id='escalation_checker',
        name='Check and escalate overdue approvals',
        replace_existing=True,
        max_instances=1
    )
    logger.info("✅ Added job: Escalation Checker (every 1 hour)")
    
    # Job 2: Task reminders - Daily at 9:00 AM
    scheduler.add_job(
        send_task_reminders,
        trigger=CronTrigger(hour=9, minute=0),
        id='task_reminders',
        name='Send task reminders',
        replace_existing=True,
        max_instances=1
    )
    logger.info("✅ Added job: Task Reminders (daily at 9:00 AM)")
    
    # Job 3: Workload sync - Every 6 hours
    scheduler.add_job(
        sync_employee_workload,
        trigger=IntervalTrigger(hours=6),
        id='workload_sync',
        name='Sync employee workload',
        replace_existing=True,
        max_instances=1
    )
    logger.info("✅ Added job: Workload Sync (every 6 hours)")
    
    # Job 4: Analytics generator - Daily at 11:00 PM
    scheduler.add_job(
        generate_daily_analytics,
        trigger=CronTrigger(hour=23, minute=0),
        id='analytics_generator',
        name='Generate daily analytics',
        replace_existing=True,
        max_instances=1
    )
    logger.info("✅ Added job: Analytics Generator (daily at 11:00 PM)")
    
    # Job 5: Cleanup - Weekly on Sunday at 2:00 AM
    scheduler.add_job(
        cleanup_old_records,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='cleanup_job',
        name='Cleanup old records',
        replace_existing=True,
        max_instances=1
    )
    logger.info("✅ Added job: Cleanup (weekly Sunday at 2:00 AM)")
    
    # Start the scheduler
    scheduler.start()
    logger.info("🚀 APScheduler started successfully with 5 jobs")
    

def stop_scheduler():
    """
    Gracefully shutdown the scheduler.
    """
    logger.info("🛑 Stopping APScheduler...")
    scheduler.shutdown()
    logger.info("✅ APScheduler stopped")


def get_scheduler_status() -> Dict[str, Any]:
    """
    Get current status of all scheduled jobs.
    """
    jobs = scheduler.get_jobs()
    
    return {
        'running': scheduler.running,
        'job_count': len(jobs),
        'jobs': [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            for job in jobs
        ]
    }

"""
Advanced Analytics Service for HRMS

Provides comprehensive analytics and reporting capabilities:
- Team productivity metrics
- Approval turnaround analytics
- Workload distribution and trends
- Task completion rates
- Department comparisons
- Historical trend analysis
- Predictive analytics
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, case, cast, Float
from sqlalchemy.sql import extract
import logging

from app.models.workflow import (
    WorkAssignment, TaskStatus, TaskPriority,
    ApprovalRequest, ApprovalStep, ApprovalStatus,
    TaskTimeLog
)
from app.models.user import Employee, Department

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for generating analytics and reports
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ============================================================================
    # TEAM PRODUCTIVITY METRICS
    # ============================================================================
    
    def get_team_productivity_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        department_id: Optional[int] = None,
        manager_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive team productivity metrics
        
        Returns:
            - Total tasks completed
            - Average completion time
            - Tasks by status distribution
            - Tasks by priority distribution
            - Completion rate by team member
            - Overdue task percentage
        """
        logger.info(f"Calculating team productivity metrics from {start_date} to {end_date}")
        
        # Base query
        query = select(WorkAssignment).where(
            and_(
                WorkAssignment.created_at >= start_date,
                WorkAssignment.created_at <= end_date
            )
        )
        
        # Apply filters
        if department_id:
            query = query.join(Employee, WorkAssignment.assignee_id == Employee.employee_id)\
                         .where(Employee.department_id == department_id)
        
        if manager_id:
            query = query.where(WorkAssignment.assigner_id == manager_id)
        
        tasks = self.session.execute(query).scalars().all()
        
        if not tasks:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0,
                "avg_completion_time_hours": 0,
                "tasks_by_status": {},
                "tasks_by_priority": {},
                "overdue_percentage": 0,
                "team_member_performance": []
            }
        
        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        
        # Convert current datetime to date for comparison with due_date
        today = datetime.utcnow().date()
        overdue_tasks = [
            t for t in tasks 
            if t.due_date and t.due_date < today and t.status != TaskStatus.COMPLETED
        ]
        
        # Average completion time
        completion_times = []
        for task in completed_tasks:
            if task.updated_at and task.created_at:
                duration = (task.updated_at - task.created_at).total_seconds() / 3600
                completion_times.append(duration)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Tasks by status
        tasks_by_status = {}
        for status in TaskStatus:
            count = len([t for t in tasks if t.status == status])
            tasks_by_status[status.value] = count
        
        # Tasks by priority
        tasks_by_priority = {}
        for priority in TaskPriority:
            count = len([t for t in tasks if t.priority == priority])
            tasks_by_priority[priority.value] = count
        
        # Team member performance
        employee_performance = {}
        for task in tasks:
            emp_id = task.assignee_id
            if emp_id not in employee_performance:
                employee_performance[emp_id] = {
                    "employee_id": emp_id,
                    "total_assigned": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "overdue": 0
                }
            
            employee_performance[emp_id]["total_assigned"] += 1
            if task.status == TaskStatus.COMPLETED:
                employee_performance[emp_id]["completed"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                employee_performance[emp_id]["in_progress"] += 1
            if task.due_date < datetime.utcnow() and task.status != TaskStatus.COMPLETED:
                employee_performance[emp_id]["overdue"] += 1
        
        # Calculate completion rates
        for emp_data in employee_performance.values():
            emp_data["completion_rate"] = (
                emp_data["completed"] / emp_data["total_assigned"] * 100
                if emp_data["total_assigned"] > 0 else 0
            )
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_tasks),
            "completion_rate": (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0,
            "avg_completion_time_hours": round(avg_completion_time, 2),
            "tasks_by_status": tasks_by_status,
            "tasks_by_priority": tasks_by_priority,
            "overdue_percentage": (len(overdue_tasks) / total_tasks * 100) if total_tasks > 0 else 0,
            "team_member_performance": list(employee_performance.values())
        }
    
    # ============================================================================
    # APPROVAL TURNAROUND ANALYTICS
    # ============================================================================
    
    def get_approval_turnaround_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        department_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate approval turnaround time analytics
        
        Returns:
            - Average approval time by type
            - Approval rates by approver
            - Escalation statistics
            - SLA compliance rate
            - Bottleneck identification
        """
        logger.info(f"Calculating approval turnaround analytics from {start_date} to {end_date}")
        
        # Get approval steps in date range
        query = select(ApprovalStep).where(
            and_(
                ApprovalStep.assigned_at >= start_date,
                ApprovalStep.assigned_at <= end_date,
                ApprovalStep.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
            )
        )
        
        steps = self.session.execute(query).scalars().all()
        
        if not steps:
            return {
                "total_approvals": 0,
                "avg_turnaround_hours": 0,
                "approval_rate": 0,
                "escalation_rate": 0,
                "sla_compliance_rate": 0,
                "turnaround_by_type": {},
                "approver_performance": []
            }
        
        # Calculate metrics
        total_steps = len(steps)
        approved_steps = [s for s in steps if s.status == ApprovalStatus.APPROVED]
        escalated_steps = [s for s in steps if s.escalated_at is not None]
        
        # Turnaround times
        turnaround_times = []
        sla_compliant = 0
        
        for step in steps:
            if step.reviewed_at and step.assigned_at:
                duration_hours = (step.reviewed_at - step.assigned_at).total_seconds() / 3600
                turnaround_times.append(duration_hours)
                
                # Check SLA compliance (default 24 hours)
                sla_hours = step.sla_hours if step.sla_hours else 24
                if duration_hours <= sla_hours:
                    sla_compliant += 1
        
        avg_turnaround = sum(turnaround_times) / len(turnaround_times) if turnaround_times else 0
        
        # Turnaround by request type
        turnaround_by_type = {}
        for step in steps:
            # Get request to find type
            request = self.session.execute(
                select(ApprovalRequest).where(ApprovalRequest.request_id == step.request_id)
            ).scalar_one_or_none()
            
            if request:
                req_type = request.request_type.value
                if req_type not in turnaround_by_type:
                    turnaround_by_type[req_type] = {
                        "count": 0,
                        "total_hours": 0,
                        "avg_hours": 0
                    }
                
                turnaround_by_type[req_type]["count"] += 1
                if step.reviewed_at and step.assigned_at:
                    hours = (step.reviewed_at - step.assigned_at).total_seconds() / 3600
                    turnaround_by_type[req_type]["total_hours"] += hours
        
        # Calculate averages
        for type_data in turnaround_by_type.values():
            if type_data["count"] > 0:
                type_data["avg_hours"] = round(type_data["total_hours"] / type_data["count"], 2)
        
        # Approver performance
        approver_performance = {}
        for step in steps:
            approver_id = step.approver_id
            if approver_id not in approver_performance:
                approver_performance[approver_id] = {
                    "approver_id": approver_id,
                    "total_reviews": 0,
                    "approved": 0,
                    "rejected": 0,
                    "avg_turnaround_hours": 0,
                    "total_hours": 0
                }
            
            approver_performance[approver_id]["total_reviews"] += 1
            if step.status == ApprovalStatus.APPROVED:
                approver_performance[approver_id]["approved"] += 1
            elif step.status == ApprovalStatus.REJECTED:
                approver_performance[approver_id]["rejected"] += 1
            
            if step.reviewed_at and step.assigned_at:
                hours = (step.reviewed_at - step.assigned_at).total_seconds() / 3600
                approver_performance[approver_id]["total_hours"] += hours
        
        # Calculate averages for approvers
        for approver_data in approver_performance.values():
            if approver_data["total_reviews"] > 0:
                approver_data["avg_turnaround_hours"] = round(
                    approver_data["total_hours"] / approver_data["total_reviews"], 2
                )
                approver_data["approval_rate"] = round(
                    approver_data["approved"] / approver_data["total_reviews"] * 100, 2
                )
        
        return {
            "total_approvals": total_steps,
            "avg_turnaround_hours": round(avg_turnaround, 2),
            "approval_rate": (len(approved_steps) / total_steps * 100) if total_steps > 0 else 0,
            "escalation_rate": (len(escalated_steps) / total_steps * 100) if total_steps > 0 else 0,
            "sla_compliance_rate": (sla_compliant / len(turnaround_times) * 100) if turnaround_times else 0,
            "turnaround_by_type": turnaround_by_type,
            "approver_performance": list(approver_performance.values())
        }
    
    # ============================================================================
    # WORKLOAD DISTRIBUTION ANALYTICS
    # ============================================================================
    
    def get_workload_distribution(
        self,
        department_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze current workload distribution across employees
        
        Returns:
            - Average utilization
            - Utilization distribution (bins)
            - Overloaded employees
            - Underutilized employees
            - Workload balance score
        """
        logger.info("Calculating workload distribution analytics")
        
        query = select(Employee)
        if department_id:
            query = query.where(Employee.department_id == department_id)
        
        employees = self.session.execute(query).scalars().all()
        
        if not employees:
            return {
                "total_employees": 0,
                "avg_utilization": 0,
                "utilization_distribution": {},
                "overloaded_employees": [],
                "underutilized_employees": [],
                "balance_score": 0
            }
        
        # Calculate utilization distribution
        utilizations = []
        overloaded = []
        underutilized = []
        
        for emp in employees:
            util = emp.utilization_percent if emp.utilization_percent else 0
            utilizations.append(util)
            
            if util > 80:
                overloaded.append({
                    "employee_id": emp.employee_id,
                    "name": emp.full_name,
                    "utilization": util,
                    "current_workload_hours": emp.current_workload_hours
                })
            elif util < 50:
                underutilized.append({
                    "employee_id": emp.employee_id,
                    "name": emp.full_name,
                    "utilization": util,
                    "current_workload_hours": emp.current_workload_hours
                })
        
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        
        # Distribution bins
        distribution = {
            "0-25%": len([u for u in utilizations if 0 <= u < 25]),
            "25-50%": len([u for u in utilizations if 25 <= u < 50]),
            "50-75%": len([u for u in utilizations if 50 <= u < 75]),
            "75-100%": len([u for u in utilizations if 75 <= u <= 100]),
            ">100%": len([u for u in utilizations if u > 100])
        }
        
        # Balance score (0-100, higher is better)
        # Based on standard deviation from ideal 70% utilization
        variance = sum((u - 70) ** 2 for u in utilizations) / len(utilizations) if utilizations else 0
        std_dev = variance ** 0.5
        balance_score = max(0, 100 - std_dev)
        
        return {
            "total_employees": len(employees),
            "avg_utilization": round(avg_utilization, 2),
            "utilization_distribution": distribution,
            "overloaded_employees": overloaded,
            "underutilized_employees": underutilized,
            "balance_score": round(balance_score, 2)
        }
    
    # ============================================================================
    # HISTORICAL TREND ANALYSIS
    # ============================================================================
    
    def get_historical_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        metric_type: str = "tasks",  # "tasks", "approvals", "workload"
        granularity: str = "daily"  # "daily", "weekly", "monthly"
    ) -> List[Dict[str, Any]]:
        """
        Generate historical trend data for time-series visualization
        
        Returns list of data points with date and values
        """
        logger.info(f"Generating {metric_type} trends from {start_date} to {end_date}")
        
        trends = []
        
        if metric_type == "tasks":
            # Task completion trends
            current_date = start_date
            while current_date <= end_date:
                if granularity == "daily":
                    next_date = current_date + timedelta(days=1)
                elif granularity == "weekly":
                    next_date = current_date + timedelta(weeks=1)
                else:  # monthly
                    next_date = current_date + timedelta(days=30)
                
                # Count tasks in this period
                completed = self.session.execute(
                    select(func.count(WorkAssignment.id)).where(
                        and_(
                            WorkAssignment.status == TaskStatus.COMPLETED,
                            WorkAssignment.updated_at >= current_date,
                            WorkAssignment.updated_at < next_date
                        )
                    )
                ).scalar() or 0
                
                created = self.session.execute(
                    select(func.count(WorkAssignment.id)).where(
                        and_(
                            WorkAssignment.created_at >= current_date,
                            WorkAssignment.created_at < next_date
                        )
                    )
                ).scalar() or 0
                
                trends.append({
                    "date": current_date.isoformat(),
                    "completed": completed,
                    "created": created
                })
                
                current_date = next_date
        
        elif metric_type == "approvals":
            # Approval processing trends
            current_date = start_date
            while current_date <= end_date:
                if granularity == "daily":
                    next_date = current_date + timedelta(days=1)
                elif granularity == "weekly":
                    next_date = current_date + timedelta(weeks=1)
                else:
                    next_date = current_date + timedelta(days=30)
                
                approved = self.session.execute(
                    select(func.count(ApprovalStep.step_id)).where(
                        and_(
                            ApprovalStep.status == ApprovalStatus.APPROVED,
                            ApprovalStep.reviewed_at >= current_date,
                            ApprovalStep.reviewed_at < next_date
                        )
                    )
                ).scalar() or 0
                
                rejected = self.session.execute(
                    select(func.count(ApprovalStep.step_id)).where(
                        and_(
                            ApprovalStep.status == ApprovalStatus.REJECTED,
                            ApprovalStep.reviewed_at >= current_date,
                            ApprovalStep.reviewed_at < next_date
                        )
                    )
                ).scalar() or 0
                
                trends.append({
                    "date": current_date.isoformat(),
                    "approved": approved,
                    "rejected": rejected
                })
                
                current_date = next_date
        
        return trends
    
    # ============================================================================
    # DEPARTMENT COMPARISON
    # ============================================================================
    
    def get_department_comparison(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Compare metrics across departments
        
        Returns list of department metrics for comparison
        """
        logger.info("Generating department comparison analytics")
        
        departments = self.session.execute(select(Department)).scalars().all()
        
        comparison = []
        
        for dept in departments:
            # Get employees in department
            employees = self.session.execute(
                select(Employee).where(Employee.department_id == dept.department_id)
            ).scalars().all()
            
            if not employees:
                continue
            
            employee_ids = [e.employee_id for e in employees]
            
            # Task metrics
            total_tasks = self.session.execute(
                select(func.count(WorkAssignment.id)).where(
                    and_(
                        WorkAssignment.assignee_id.in_(employee_ids),
                        WorkAssignment.created_at >= start_date,
                        WorkAssignment.created_at <= end_date
                    )
                )
            ).scalar() or 0
            
            completed_tasks = self.session.execute(
                select(func.count(WorkAssignment.id)).where(
                    and_(
                        WorkAssignment.assignee_id.in_(employee_ids),
                        WorkAssignment.status == TaskStatus.COMPLETED,
                        WorkAssignment.created_at >= start_date,
                        WorkAssignment.created_at <= end_date
                    )
                )
            ).scalar() or 0
            
            # Approval metrics
            total_approvals = self.session.execute(
                select(func.count(ApprovalStep.step_id)).where(
                    and_(
                        ApprovalStep.approver_id.in_(employee_ids),
                        ApprovalStep.assigned_at >= start_date,
                        ApprovalStep.assigned_at <= end_date
                    )
                )
            ).scalar() or 0
            
            # Utilization
            avg_utilization = sum(
                e.utilization_percent for e in employees if e.utilization_percent
            ) / len(employees) if employees else 0
            
            comparison.append({
                "department_id": dept.department_id,
                "department_name": dept.name,
                "employee_count": len(employees),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "total_approvals": total_approvals,
                "avg_utilization": round(avg_utilization, 2)
            })
        
        return comparison
    
    # ============================================================================
    # COMPREHENSIVE DASHBOARD DATA
    # ============================================================================
    
    def get_dashboard_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary combining all metrics
        """
        logger.info("Generating comprehensive dashboard summary")
        
        return {
            "productivity": self.get_team_productivity_metrics(start_date, end_date),
            "approvals": self.get_approval_turnaround_analytics(start_date, end_date),
            "workload": self.get_workload_distribution(),
            "trends": {
                "tasks": self.get_historical_trends(start_date, end_date, "tasks", "daily"),
                "approvals": self.get_historical_trends(start_date, end_date, "approvals", "daily")
            },
            "departments": self.get_department_comparison(start_date, end_date),
            "generated_at": datetime.utcnow().isoformat()
        }

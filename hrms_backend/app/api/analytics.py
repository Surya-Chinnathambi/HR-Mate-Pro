"""
Analytics API Router

Provides endpoints for accessing analytics and reports
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models.user import User
from app.database import get_session
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/productivity")
async def get_productivity_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    manager_id: Optional[int] = Query(None, description="Filter by manager"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get team productivity metrics
    
    Returns:
        - Total tasks, completion rate
        - Average completion time
        - Tasks by status and priority
        - Team member performance
    """
    # Default to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(session)
    return analytics_service.get_team_productivity_metrics(
        start_date, end_date, department_id, manager_id
    )


@router.get("/approvals")
async def get_approval_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get approval turnaround analytics
    
    Returns:
        - Average turnaround time
        - Approval rates
        - Escalation statistics
        - SLA compliance
        - Approver performance
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(session)
    return analytics_service.get_approval_turnaround_analytics(
        start_date, end_date, department_id
    )


@router.get("/workload")
async def get_workload_analytics(
    department_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get current workload distribution analytics
    
    Returns:
        - Average utilization
        - Utilization distribution
        - Overloaded and underutilized employees
        - Workload balance score
    """
    analytics_service = AnalyticsService(session)
    return analytics_service.get_workload_distribution(department_id)


@router.get("/trends")
async def get_historical_trends(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    metric_type: str = Query("tasks", description="Type: tasks, approvals, workload"),
    granularity: str = Query("daily", description="Granularity: daily, weekly, monthly"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get historical trend data for time-series charts
    
    Supports different metric types and time granularities
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(session)
    return analytics_service.get_historical_trends(
        start_date, end_date, metric_type, granularity
    )


@router.get("/departments")
async def get_department_comparison(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get comparison metrics across all departments
    
    Returns list of department metrics for comparison views
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(session)
    return analytics_service.get_department_comparison(start_date, end_date)


@router.get("/dashboard")
async def get_dashboard_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get comprehensive dashboard summary
    
    Returns all analytics combined for dashboard view
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(session)
    return analytics_service.get_dashboard_summary(start_date, end_date, current_user.user_id)

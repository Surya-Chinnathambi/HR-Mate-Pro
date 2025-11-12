"""
Scheduler Management API Router

Provides endpoints to manage and monitor scheduled background jobs.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime

from app.core.security import get_current_user
from app.models.user import User
from app.services.scheduler import (
    get_scheduler_status,
    check_and_escalate_approvals,
    send_task_reminders,
    sync_employee_workload,
    generate_daily_analytics,
    cleanup_old_records
)

router = APIRouter()


@router.get("/status")
async def get_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of the scheduler and all jobs.
    
    Returns:
        - running: Whether scheduler is active
        - job_count: Number of registered jobs
        - jobs: List of job details with next run times
    """
    status = get_scheduler_status()
    return {
        **status,
        'server_time': datetime.utcnow().isoformat()
    }


@router.post("/jobs/escalation/run")
async def trigger_escalation_job(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the escalation checker job.
    Admin use only for testing or immediate escalation needs.
    """
    try:
        await check_and_escalate_approvals()
        return {
            'status': 'success',
            'message': 'Escalation check completed',
            'triggered_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@router.post("/jobs/reminders/run")
async def trigger_reminder_job(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the task reminder job.
    """
    try:
        await send_task_reminders()
        return {
            'status': 'success',
            'message': 'Task reminders sent',
            'triggered_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@router.post("/jobs/workload-sync/run")
async def trigger_workload_sync_job(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the workload sync job.
    """
    try:
        await sync_employee_workload()
        return {
            'status': 'success',
            'message': 'Workload sync completed',
            'triggered_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@router.post("/jobs/analytics/run")
async def trigger_analytics_job(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the analytics generation job.
    """
    try:
        await generate_daily_analytics()
        return {
            'status': 'success',
            'message': 'Analytics generated',
            'triggered_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@router.post("/jobs/cleanup/run")
async def trigger_cleanup_job(
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger the cleanup job.
    Use with caution - this deletes old records.
    """
    try:
        await cleanup_old_records()
        return {
            'status': 'success',
            'message': 'Cleanup completed',
            'triggered_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")

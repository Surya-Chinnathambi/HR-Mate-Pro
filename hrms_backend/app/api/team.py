"""
Team API
Manager's team information and analytics
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel

from app.database import get_async_session
from app.core.security import get_current_active_user, require_permission
from app.models.user import User

router = APIRouter(prefix="/team", tags=["team"])


@router.get("/members")
@require_permission("team", "read", scope="team")
async def get_team_members(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status_filter: Optional[str] = None,  # active, inactive
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get team members for current manager
    
    Requires: team:read permission with scope=team (Manager only)
    Returns employees reporting to current manager
    """
    try:
        # Get manager's employee_id
        manager_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(manager_query, {"user_id": current_user.id})
        manager = result.fetchone()
        
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager employee profile not found"
            )
        
        manager_employee_id = manager[0]
        
        # Build query with optional status filter
        where_clause = "WHERE manager_id = :manager_id"
        if status_filter:
            where_clause += f" AND status = :status"
        
        members_query = text(f"""
            SELECT 
                id,
                first_name,
                last_name,
                email,
                role,
                department_id,
                status,
                hire_date,
                phone_number
            FROM employees
            {where_clause}
            ORDER BY first_name, last_name
            LIMIT :limit OFFSET :skip
        """)
        
        params = {
            "manager_id": manager_employee_id,
            "limit": limit,
            "skip": skip
        }
        if status_filter:
            params["status"] = status_filter
        
        result = await db.execute(members_query, params)
        
        members = []
        for row in result.fetchall():
            members.append({
                "employee_id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "full_name": f"{row[1]} {row[2]}",
                "email": row[3],
                "role": row[4],
                "department_id": row[5],
                "status": row[6],
                "hire_date": row[7].isoformat() if row[7] else None,
                "phone_number": row[8]
            })
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*) FROM employees {where_clause}
        """)
        
        count_result = await db.execute(count_query, params)
        total = count_result.scalar()
        
        return {
            "members": members,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching team members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team members"
        )


@router.get("/workload")
@require_permission("team", "read", scope="team")
async def get_team_workload(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get team workload distribution
    
    Shows active tasks per team member
    """
    try:
        # Get manager's employee_id
        manager_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(manager_query, {"user_id": current_user.id})
        manager = result.fetchone()
        
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager employee profile not found"
            )
        
        manager_employee_id = manager[0]
        
        # Get workload for each team member
        workload_query = text("""
            SELECT 
                e.id,
                e.first_name || ' ' || e.last_name as name,
                COUNT(CASE WHEN t.status IN ('pending', 'in_progress') THEN 1 END) as active_tasks,
                COUNT(CASE WHEN t.status = 'completed' AND t.completed_at >= NOW() - INTERVAL '7 days' THEN 1 END) as completed_this_week,
                COUNT(CASE WHEN t.priority = 'urgent' AND t.status IN ('pending', 'in_progress') THEN 1 END) as urgent_tasks,
                COUNT(CASE WHEN t.due_date < NOW() AND t.status IN ('pending', 'in_progress') THEN 1 END) as overdue_tasks
            FROM employees e
            LEFT JOIN tasks t ON t.assigned_to_employee_id = e.id
            WHERE e.manager_id = :manager_id AND e.status = 'active'
            GROUP BY e.id, e.first_name, e.last_name
            ORDER BY active_tasks DESC, urgent_tasks DESC
        """)
        
        result = await db.execute(workload_query, {
            "manager_id": manager_employee_id
        })
        
        workload = []
        for row in result.fetchall():
            workload.append({
                "employee_id": row[0],
                "name": row[1],
                "active_tasks": row[2] or 0,
                "completed_this_week": row[3] or 0,
                "urgent_tasks": row[4] or 0,
                "overdue_tasks": row[5] or 0,
                "workload_status": "high" if (row[2] or 0) > 10 else "medium" if (row[2] or 0) > 5 else "low"
            })
        
        return {
            "workload": workload,
            "total_members": len(workload)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching team workload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team workload"
        )


@router.get("/attendance")
@require_permission("team", "read", scope="team")
async def get_team_attendance(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get team attendance summary
    
    Shows attendance status for team members
    """
    try:
        # Get manager's employee_id
        manager_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(manager_query, {"user_id": current_user.id})
        manager = result.fetchone()
        
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager employee profile not found"
            )
        
        manager_employee_id = manager[0]
        
        # Default to today if no date range specified
        if not date_from:
            date_from = date.today()
        if not date_to:
            date_to = date.today()
        
        # Get attendance for team members
        attendance_query = text("""
            SELECT 
                e.id,
                e.first_name || ' ' || e.last_name as name,
                a.date,
                a.check_in_time,
                a.check_out_time,
                a.status,
                a.hours_worked
            FROM employees e
            LEFT JOIN attendance_records a ON a.employee_id = e.id
                AND a.date BETWEEN :date_from AND :date_to
            WHERE e.manager_id = :manager_id AND e.status = 'active'
            ORDER BY e.first_name, e.last_name, a.date DESC
        """)
        
        result = await db.execute(attendance_query, {
            "manager_id": manager_employee_id,
            "date_from": date_from,
            "date_to": date_to
        })
        
        attendance = []
        for row in result.fetchall():
            attendance.append({
                "employee_id": row[0],
                "name": row[1],
                "date": row[2].isoformat() if row[2] else None,
                "check_in_time": row[3].isoformat() if row[3] else None,
                "check_out_time": row[4].isoformat() if row[4] else None,
                "status": row[5],  # present, absent, on_leave, wfh
                "hours_worked": float(row[6]) if row[6] else None
            })
        
        # Calculate summary stats
        summary = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "records": attendance,
            "total_records": len(attendance)
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching team attendance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team attendance"
        )


@router.get("/leaves")
@require_permission("team", "read", scope="team")
async def get_team_leaves(
    status_filter: Optional[str] = Query(None),  # pending, approved, rejected
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get team leave requests
    
    Shows pending and upcoming leaves for team members
    """
    try:
        # Get manager's employee_id
        manager_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(manager_query, {"user_id": current_user.id})
        manager = result.fetchone()
        
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager employee profile not found"
            )
        
        manager_employee_id = manager[0]
        
        # Build query with optional status filter
        where_clause = """
            WHERE e.manager_id = :manager_id 
            AND e.status = 'active'
        """
        if status_filter:
            where_clause += f" AND lr.status = :status"
        
        leaves_query = text(f"""
            SELECT 
                lr.id,
                e.id as employee_id,
                e.first_name || ' ' || e.last_name as name,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.days_count,
                lr.status,
                lr.reason,
                lr.created_at
            FROM leave_requests lr
            INNER JOIN employees e ON e.id = lr.employee_id
            {where_clause}
            ORDER BY 
                CASE lr.status 
                    WHEN 'pending' THEN 1 
                    WHEN 'approved' THEN 2 
                    WHEN 'rejected' THEN 3 
                END,
                lr.start_date DESC
        """)
        
        params = {"manager_id": manager_employee_id}
        if status_filter:
            params["status"] = status_filter
        
        result = await db.execute(leaves_query, params)
        
        leaves = []
        for row in result.fetchall():
            leaves.append({
                "leave_request_id": row[0],
                "employee_id": row[1],
                "employee_name": row[2],
                "leave_type": row[3],
                "start_date": row[4].isoformat() if row[4] else None,
                "end_date": row[5].isoformat() if row[5] else None,
                "days_count": row[6],
                "status": row[7],
                "reason": row[8],
                "requested_at": row[9].isoformat() if row[9] else None
            })
        
        # Count by status
        status_counts_query = text("""
            SELECT lr.status, COUNT(*) 
            FROM leave_requests lr
            INNER JOIN employees e ON e.id = lr.employee_id
            WHERE e.manager_id = :manager_id AND e.status = 'active'
            GROUP BY lr.status
        """)
        
        status_result = await db.execute(status_counts_query, {
            "manager_id": manager_employee_id
        })
        
        status_counts = {}
        for row in status_result.fetchall():
            status_counts[row[0]] = row[1]
        
        return {
            "leaves": leaves,
            "total": len(leaves),
            "status_counts": status_counts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching team leaves: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team leaves"
        )


@router.get("/performance-summary")
@require_permission("team", "read", scope="team")
async def get_team_performance_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get team performance summary
    
    Aggregated metrics for manager's team
    """
    try:
        # Get manager's employee_id
        manager_query = text("""
            SELECT id FROM employees WHERE user_id = :user_id
        """)
        result = await db.execute(manager_query, {"user_id": current_user.id})
        manager = result.fetchone()
        
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager employee profile not found"
            )
        
        manager_employee_id = manager[0]
        
        # Get comprehensive team metrics
        metrics_query = text("""
            SELECT 
                COUNT(DISTINCT e.id) as total_members,
                COUNT(DISTINCT CASE WHEN t.status IN ('pending', 'in_progress') THEN t.id END) as active_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_tasks,
                COUNT(DISTINCT CASE WHEN lr.status = 'pending' THEN lr.id END) as pending_leaves,
                AVG(CASE WHEN a.date >= CURRENT_DATE - INTERVAL '30 days' THEN a.hours_worked END) as avg_hours_worked_30d
            FROM employees e
            LEFT JOIN tasks t ON t.assigned_to_employee_id = e.id
            LEFT JOIN leave_requests lr ON lr.employee_id = e.id
            LEFT JOIN attendance_records a ON a.employee_id = e.id
            WHERE e.manager_id = :manager_id AND e.status = 'active'
        """)
        
        result = await db.execute(metrics_query, {
            "manager_id": manager_employee_id
        })
        
        row = result.fetchone()
        
        return {
            "team_size": row[0] or 0,
            "active_tasks": row[1] or 0,
            "completed_tasks": row[2] or 0,
            "pending_leaves": row[3] or 0,
            "avg_hours_worked_30_days": round(float(row[4]) if row[4] else 0, 2),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching team performance summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch team performance summary"
        )

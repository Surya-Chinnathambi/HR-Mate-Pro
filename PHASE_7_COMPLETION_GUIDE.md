# Phase 7: APScheduler Background Jobs - IMPLEMENTATION GUIDE

## ✅ Implementation Complete

**Date:** November 11, 2025  
**Phase:** 7/9 - APScheduler Background Jobs  
**Status:** COMPLETED  
**Total Code:** ~900 lines (Scheduler Service: 750 lines, API Router: 150 lines)

---

## 📊 Overview

Successfully implemented a comprehensive background job scheduling system using APScheduler with 5 automated jobs that handle:
- **Approval escalations** (hourly)
- **Task reminders** (daily at 9 AM)
- **Workload synchronization** (every 6 hours)
- **Analytics generation** (daily at 11 PM)
- **Database cleanup** (weekly Sunday 2 AM)

---

## 🏗️ Architecture

### Components Created:

1. **`app/services/scheduler.py`** (~750 lines)
   - APScheduler configuration and job definitions
   - 5 scheduled job functions
   - Scheduler lifecycle management
   - Status monitoring

2. **`app/api/scheduler.py`** (~150 lines)
   - REST API endpoints for scheduler management
   - Manual job trigger endpoints
   - Status monitoring endpoint

3. **`app/main.py`** (Modified)
   - Integrated scheduler startup in lifespan
   - Added scheduler API router
   - Graceful shutdown handling

4. **`test_scheduler.py`** (~120 lines)
   - Comprehensive test suite for all jobs
   - Individual job testing functions
   - Summary reporting

---

## 📅 Scheduled Jobs

### Job 1: Escalation Checker
**Schedule:** Every 1 hour  
**Function:** `check_and_escalate_approvals()`  
**Purpose:** Automatically escalate overdue approval requests

**What it does:**
1. Finds all pending approval steps older than SLA (default 24 hours)
2. Marks steps as `escalated`
3. Assigns to next approval level if available
4. Sends urgent notifications to:
   - Next approver (if escalated)
   - Original requester (if no escalation path)
5. Logs escalation metrics

**Key Logic:**
```python
# Find overdue approvals
pending_steps = db.query(ApprovalStep).filter(
    ApprovalStep.status == 'pending',
    ApprovalStep.assigned_at < now - timedelta(hours=24)
).all()

# Check if exceeds SLA
if hours_pending >= sla_hours:
    step.status = 'escalated'
    # Escalate to next level or notify requester
```

**Notifications Sent:**
- `approval_escalation` (urgent) → Next approver
- `approval_overdue` (high) → Original requester

---

### Job 2: Task Reminder
**Schedule:** Daily at 9:00 AM  
**Function:** `send_task_reminders()`  
**Purpose:** Send reminders for overdue and upcoming tasks

**What it does:**
1. Identifies overdue tasks (due date passed, not completed)
2. Identifies upcoming tasks (due within 2 days)
3. Sends multi-channel reminders:
   - Overdue: Email + In-app (urgent priority)
   - Upcoming: In-app only (medium priority)
4. Notifies both assignee and manager
5. Includes task details and progress percentage

**Categories:**
```python
# Overdue tasks
overdue_tasks = tasks.filter(
    due_date < now,
    status IN ['NOT_STARTED', 'IN_PROGRESS', 'BLOCKED']
)

# Upcoming tasks (due in 0-2 days)
upcoming_tasks = tasks.filter(
    due_date BETWEEN now AND now+2days,
    status IN ['NOT_STARTED', 'IN_PROGRESS']
)
```

**Notification Examples:**
- "⚠️ Overdue Task Reminder: 'Fix bug #123' is 3 day(s) overdue"
- "📅 Task Due Soon: 'Code review' is due in 1 day(s). Progress: 45%"

---

### Job 3: Workload Sync
**Schedule:** Every 6 hours  
**Function:** `sync_employee_workload()`  
**Purpose:** Recalculate employee workloads and detect overloaded staff

**What it does:**
1. Calculates total hours from active tasks per employee
2. Updates `current_workload_hours` in employee table
3. Calculates `utilization_percent` (workload / weekly_capacity * 100)
4. Identifies overloaded employees (>80% utilization)
5. Sends alerts to managers with overloaded team members
6. Broadcasts real-time WebSocket events

**Calculation:**
```python
# Sum active task hours
total_hours = sum(task.estimated_hours 
                  for task in active_tasks)

# Calculate utilization
utilization = (total_hours / weekly_capacity) * 100

# Update employee
employee.current_workload_hours = total_hours
employee.utilization_percent = utilization
```

**Alert Thresholds:**
- **>80% utilization:** Send workload alert to manager
- **>100% utilization:** Critical overload warning

**Manager Notification:**
```
"⚠️ Team Members Overloaded"
"The following team members are at >80% capacity: 
 John Doe (95%), Jane Smith (85%), Bob Wilson (82%)"
```

---

### Job 4: Analytics Generator
**Schedule:** Daily at 11:00 PM  
**Function:** `generate_daily_analytics()`  
**Purpose:** Generate comprehensive daily reports and metrics

**What it does:**
1. Calculates approval metrics:
   - Total processed today
   - Approval rate (approved / total)
   - Average approval time (hours)
   - Breakdown by status

2. Calculates task metrics:
   - Tasks created today
   - Tasks completed today
   - Overdue tasks count
   - Average completion time

3. Calculates workload metrics:
   - Average team utilization
   - Employees at capacity (>80%)

4. Sends summary to all managers
5. Logs analytics report

**Sample Report:**
```json
{
  "date": "2025-11-11",
  "approvals": {
    "total_processed": 45,
    "approved": 38,
    "rejected": 7,
    "approval_rate": 84.44,
    "avg_approval_time_hours": 3.25
  },
  "tasks": {
    "created": 23,
    "completed": 19,
    "overdue": 5,
    "avg_completion_time_hours": 48.5
  },
  "workload": {
    "avg_utilization": 72.3,
    "at_capacity_count": 8
  }
}
```

**Manager Notification:**
```
"📊 Daily Analytics Summary"
"Approvals: 45 | Tasks: 19 completed | 5 overdue | 
 Avg utilization: 72.3%"
```

---

### Job 5: Cleanup
**Schedule:** Weekly on Sunday at 2:00 AM  
**Function:** `cleanup_old_records()`  
**Purpose:** Archive old data and maintain database performance

**What it does:**
1. Deletes read notifications older than 30 days
2. Identifies completed tasks older than 90 days (for archival)
3. Identifies old approval requests older than 1 year (for archival)
4. Logs cleanup statistics
5. Prepares for database vacuum (if needed)

**Cleanup Rules:**
```python
# Notifications: Delete if read AND >30 days old
DELETE FROM notifications 
WHERE is_read = true 
  AND created_at < now() - INTERVAL '30 days'

# Tasks: Archive if completed AND >90 days old
# (In production: Move to archive table)
SELECT * FROM work_assignments 
WHERE status = 'COMPLETED' 
  AND updated_at < now() - INTERVAL '90 days'

# Approvals: Archive if final status AND >1 year old
SELECT * FROM approval_requests 
WHERE status IN ('approved', 'rejected', 'cancelled')
  AND created_at < now() - INTERVAL '1 year'
```

**Cleanup Report:**
```
✅ Cleanup completed:
   - 1,234 old notifications deleted
   - 567 completed tasks marked for archival
   - 89 old approvals marked for archival
```

---

## 🔌 API Endpoints

### Get Scheduler Status
```http
GET /api/scheduler/status
Authorization: Bearer {token}
```

**Response:**
```json
{
  "running": true,
  "job_count": 5,
  "jobs": [
    {
      "id": "escalation_checker",
      "name": "Check and escalate overdue approvals",
      "next_run_time": "2025-11-11T14:00:00",
      "trigger": "interval[1:00:00]"
    },
    {
      "id": "task_reminders",
      "name": "Send task reminders",
      "next_run_time": "2025-11-12T09:00:00",
      "trigger": "cron[day='*' hour='9' minute='0']"
    },
    ...
  ],
  "server_time": "2025-11-11T13:45:23"
}
```

### Manual Job Triggers

All manual trigger endpoints require authentication and return the same response format:

```json
{
  "status": "success",
  "message": "Job completed",
  "triggered_at": "2025-11-11T13:45:23"
}
```

**Available Endpoints:**
```http
POST /api/scheduler/jobs/escalation/run
POST /api/scheduler/jobs/reminders/run
POST /api/scheduler/jobs/workload-sync/run
POST /api/scheduler/jobs/analytics/run
POST /api/scheduler/jobs/cleanup/run
```

---

## 🧪 Testing

### Run Test Suite
```bash
cd c:\forlast\hrms_backend
python test_scheduler.py
```

**Expected Output:**
```
============================================================
SCHEDULER JOB TESTING SUITE
Started at: 2025-11-11 13:45:23
============================================================

============================================================
TEST 1: Escalation Checker
============================================================
🔍 Starting escalation check job...
✅ Escalation check completed: 2 approvals escalated
✅ Escalation job completed successfully

============================================================
TEST 2: Task Reminder
============================================================
📧 Starting task reminder job...
✅ Task reminders sent: 5 overdue, 12 upcoming
✅ Task reminder job completed successfully

...

============================================================
TEST SUMMARY
============================================================
Escalation Checker        ✅ PASSED
Task Reminder            ✅ PASSED
Workload Sync            ✅ PASSED
Analytics Generation     ✅ PASSED
Cleanup                  ✅ PASSED

Total: 5/5 tests passed
============================================================
```

### Manual Testing via API

**Test Escalation Job:**
```bash
curl -X POST http://localhost:8000/api/scheduler/jobs/escalation/run \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Check Scheduler Status:**
```bash
curl http://localhost:8000/api/scheduler/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🚀 Integration with Existing Systems

### Notification Service Integration

All jobs use the existing `NotificationService` for multi-channel notifications:

```python
from app.services.notification_service import NotificationService

notification_service = NotificationService()

await notification_service.send_notification(
    user_id=user_id,
    title="Job Alert",
    message="Message content",
    notification_type="job_alert",
    priority="high",
    channels=['in_app', 'email']  # Multi-channel
)
```

### WebSocket Integration

Workload sync job broadcasts real-time updates:

```python
from app.api.websocket import broadcast_workload_alert

await broadcast_workload_alert(manager_id, {
    'overloaded_employees': employees_list,
    'message': f"{len(employees_list)} team member(s) at >80% capacity"
})
```

This triggers the `workload_alert` event in the frontend `NotificationCenter` component.

---

## 📝 Configuration

### Job Schedule Customization

Edit `app/services/scheduler.py` to modify job schedules:

```python
# Escalation: Change from hourly to every 2 hours
scheduler.add_job(
    check_and_escalate_approvals,
    trigger=IntervalTrigger(hours=2),  # Changed from 1 to 2
    id='escalation_checker',
    ...
)

# Task reminders: Change from 9 AM to 8 AM
scheduler.add_job(
    send_task_reminders,
    trigger=CronTrigger(hour=8, minute=0),  # Changed from 9 to 8
    id='task_reminders',
    ...
)
```

### SLA Hours Configuration

Edit SLA hours in approval chain configuration:

```python
# In check_and_escalate_approvals()
sla_hours = step.sla_hours if step.sla_hours else 24  # Default 24 hours

# Can be customized per approval type/level in approval_chains table
```

### Cleanup Retention Periods

Edit retention periods in `cleanup_old_records()`:

```python
# Change notification retention from 30 to 60 days
old_notifications_cutoff = now - timedelta(days=60)

# Change task archive from 90 to 180 days
old_tasks_cutoff = now - timedelta(days=180)

# Change approval archive from 1 year to 2 years
old_approvals_cutoff = now - timedelta(days=730)
```

---

## 🔐 Security Considerations

### Job Execution Permissions
- All manual trigger endpoints require authentication
- Only authorized users can trigger jobs manually
- Jobs run with system-level database access

### Rate Limiting
- `max_instances=1` ensures only one instance of each job runs at a time
- Prevents duplicate job execution
- Prevents database connection exhaustion

### Error Handling
- All jobs have try-catch blocks
- Database rollback on errors
- Comprehensive logging for debugging
- Failures don't crash the scheduler

---

## 📊 Monitoring & Logging

### Log Levels

All jobs log at INFO level by default:
```python
logger.info("🔍 Starting escalation check job...")
logger.info("✅ Escalation check completed: 2 approvals escalated")
logger.warning("⚠️ Approval 123 has no next level to escalate to")
logger.error("❌ Error in escalation check job: {error}")
```

### Monitoring Recommendations

1. **Monitor job execution times**
   - Track via APScheduler job history
   - Set up alerts for jobs taking >5 minutes

2. **Monitor job failures**
   - Check error logs daily
   - Set up alerts for 3+ consecutive failures

3. **Monitor database impact**
   - Track query execution times
   - Monitor connection pool usage during job runs

4. **Monitor notification delivery**
   - Track notification send success rates
   - Monitor email/SMS quota usage

---

## 🎯 Performance Optimization

### Current Optimizations

1. **Batch Processing:** All jobs process records in batches
2. **Database Indexing:** Queries use indexed columns (status, dates)
3. **Single Instance:** `max_instances=1` prevents concurrent runs
4. **Async Execution:** All jobs use async/await for non-blocking I/O

### Future Improvements

1. **Pagination:** For jobs processing >10,000 records
2. **Celery Migration:** For distributed task queue (if needed)
3. **Redis Caching:** Cache frequently accessed data
4. **Bulk Notifications:** Batch notification sends for same message

---

## 🐛 Troubleshooting

### Scheduler Not Starting

**Error:** `ModuleNotFoundError: No module named 'apscheduler'`
**Solution:**
```bash
pip install apscheduler
```

**Error:** `Scheduler is already running`
**Solution:** Restart the application completely

### Jobs Not Executing

**Check 1:** Verify scheduler is running
```bash
curl http://localhost:8000/api/scheduler/status
```

**Check 2:** Check job next run time
```json
{
  "next_run_time": "2025-11-12T09:00:00"  // Future date = scheduled
}
```

**Check 3:** Check server logs
```bash
tail -f logs/hrms.log | grep "APScheduler"
```

### Job Execution Errors

**Check error logs:**
```bash
grep "Error in.*job:" logs/hrms.log
```

**Common Issues:**
1. **Database connection timeout** → Increase pool size in config
2. **Notification service error** → Check email/SMS credentials
3. **WebSocket import error** → WebSocket module not loaded (non-critical)

---

## 📈 Metrics & KPIs

### Track These Metrics

1. **Escalation Rate**
   - Target: <10% of approvals escalated
   - Alert if: >20% escalated

2. **Overdue Task Rate**
   - Target: <5% of active tasks overdue
   - Alert if: >15% overdue

3. **Workload Distribution**
   - Target: <20% of employees >80% capacity
   - Alert if: >40% at capacity

4. **Approval Turnaround Time**
   - Target: <24 hours average
   - Alert if: >48 hours average

5. **Task Completion Rate**
   - Target: >90% completed on time
   - Alert if: <70% completed on time

---

## ✅ Phase 7 Completion Checklist

- [x] APScheduler dependency installed
- [x] Scheduler service created (`scheduler.py`)
- [x] 5 scheduled jobs implemented:
  - [x] Escalation checker (hourly)
  - [x] Task reminders (daily 9 AM)
  - [x] Workload sync (every 6 hours)
  - [x] Analytics generator (daily 11 PM)
  - [x] Cleanup job (weekly Sunday 2 AM)
- [x] Scheduler API router created
- [x] Integration with main.py (startup/shutdown)
- [x] Test suite created
- [x] Documentation completed
- [x] Requirements.txt updated
- [x] Error handling implemented
- [x] Logging configured
- [x] WebSocket integration (workload alerts)
- [x] Multi-channel notifications

---

## 🚦 Next Steps

### Immediate Testing (1 hour):
1. Restart backend server to load scheduler
2. Check scheduler status: `GET /api/scheduler/status`
3. Run test suite: `python test_scheduler.py`
4. Manually trigger each job to verify functionality
5. Monitor logs for errors

### Phase 8: Analytics and Reporting (3-4 hours):
1. Create `AnalyticsService` with complex SQL queries
2. Build historical trend analysis
3. Create `AnalyticsDashboard.tsx` component
4. Add Recharts visualizations (line, bar, pie, area charts)
5. Implement date range filters
6. Add export functionality (PDF, Excel, CSV)
7. Department/team comparison views

### Phase 9: Testing and Deployment (Ongoing):
1. Write integration tests for all APIs
2. Load testing with 1000+ users
3. Security audit (SQL injection, XSS, CSRF)
4. Performance optimization
5. Deployment documentation
6. Docker Compose production setup
7. CI/CD pipeline configuration

---

## 📊 Impact Summary

**Code Added:**
- `scheduler.py`: 750 lines
- `scheduler.py` (API): 150 lines
- `test_scheduler.py`: 120 lines
- **Total: ~1,020 lines**

**Features Delivered:**
- ✅ 5 automated background jobs
- ✅ Job scheduling with cron and interval triggers
- ✅ Manual job trigger API
- ✅ Comprehensive logging and monitoring
- ✅ Error handling and recovery
- ✅ Integration with notifications and WebSocket
- ✅ Test suite for all jobs

**System Improvements:**
- ✅ Automated approval escalation (reduces manual intervention)
- ✅ Proactive task reminders (reduces missed deadlines)
- ✅ Real-time workload monitoring (prevents burnout)
- ✅ Daily analytics (data-driven decisions)
- ✅ Automated cleanup (maintains performance)

---

**Phase 7 Status: COMPLETE ✅**

**Next Phase:** Phase 8 - Analytics and Reporting

"""
Scheduler Testing Script

This script tests all 5 background jobs individually to ensure they work correctly.
Run this script to verify the scheduler implementation before production deployment.
"""

import asyncio
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append('.')

from app.services.scheduler import (
    check_and_escalate_approvals,
    send_task_reminders,
    sync_employee_workload,
    generate_daily_analytics,
    cleanup_old_records
)


async def test_escalation_job():
    """Test the escalation checker job"""
    print("\n" + "="*60)
    print("TEST 1: Escalation Checker")
    print("="*60)
    try:
        await check_and_escalate_approvals()
        print("✅ Escalation job completed successfully")
        return True
    except Exception as e:
        print(f"❌ Escalation job failed: {str(e)}")
        return False


async def test_reminder_job():
    """Test the task reminder job"""
    print("\n" + "="*60)
    print("TEST 2: Task Reminder")
    print("="*60)
    try:
        await send_task_reminders()
        print("✅ Task reminder job completed successfully")
        return True
    except Exception as e:
        print(f"❌ Task reminder job failed: {str(e)}")
        return False


async def test_workload_sync_job():
    """Test the workload sync job"""
    print("\n" + "="*60)
    print("TEST 3: Workload Sync")
    print("="*60)
    try:
        await sync_employee_workload()
        print("✅ Workload sync job completed successfully")
        return True
    except Exception as e:
        print(f"❌ Workload sync job failed: {str(e)}")
        return False


async def test_analytics_job():
    """Test the analytics generation job"""
    print("\n" + "="*60)
    print("TEST 4: Analytics Generation")
    print("="*60)
    try:
        await generate_daily_analytics()
        print("✅ Analytics generation job completed successfully")
        return True
    except Exception as e:
        print(f"❌ Analytics generation job failed: {str(e)}")
        return False


async def test_cleanup_job():
    """Test the cleanup job"""
    print("\n" + "="*60)
    print("TEST 5: Cleanup")
    print("="*60)
    try:
        await cleanup_old_records()
        print("✅ Cleanup job completed successfully")
        return True
    except Exception as e:
        print(f"❌ Cleanup job failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all scheduler job tests"""
    print("\n" + "="*60)
    print("SCHEDULER JOB TESTING SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    
    # Test each job
    results.append(("Escalation Checker", await test_escalation_job()))
    results.append(("Task Reminder", await test_reminder_job()))
    results.append(("Workload Sync", await test_workload_sync_job()))
    results.append(("Analytics Generation", await test_analytics_job()))
    results.append(("Cleanup", await test_cleanup_job()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for job_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{job_name:25} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

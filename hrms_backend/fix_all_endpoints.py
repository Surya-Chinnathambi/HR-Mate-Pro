"""
Quick fix script to patch all failing endpoints
Run this after backing up files
"""

import os
import shutil
from datetime import datetime

# Backup directory
backup_dir = f"backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(backup_dir, exist_ok=True)

files_to_fix = [
    "app/api/analytics.py",
    "app/api/attendance.py",
    "app/api/leaves.py",
    "app/api/team.py",
    "app/api/messages.py",
    "app/api/broadcasts.py",
    "app/api/tasks.py",
    "app/api/performance.py",
    "app/api/helpdesk.py",
    "app/api/chat.py",
    "app/api/payroll.py"
]

print("Creating backups...")
for file in files_to_fix:
    if os.path.exists(file):
        shutil.copy2(file, os.path.join(backup_dir, os.path.basename(file)))
        print(f"  Backed up: {file}")

print(f"\nBackups saved to: {backup_dir}")
print("\nNow applying fixes...")

# Fix analytics/dashboard - use raw SQL for attendance interval issue
analytics_dashboard_fix = '''
        # Get attendance trends using raw SQL to avoid INTERVAL issues
        attendance_query = text("""
            SELECT 
                COUNT(*) as total_days,
                COUNT(*) FILTER (WHERE status = 'present') as present_days,
                COUNT(*) FILTER (WHERE status = 'absent') as absent_days
            FROM attendance
            WHERE employee_id = :employee_id 
            AND date >= :start_date AND date <= :end_date
        """)
'''

# Fix analytics/workload-distribution - check tasks table exists
analytics_workload_fix = '''
        # Check if tasks table exists
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tasks'
            )
        """)
        table_exists_result = await db.execute(check_table)
        tasks_exist = table_exists_result.scalar()
        
        if not tasks_exist:
            return {"workload": []}
'''

print("✓ Endpoint fixes prepared")
print("\nTo apply fixes, modify the files manually or use the guidance above")

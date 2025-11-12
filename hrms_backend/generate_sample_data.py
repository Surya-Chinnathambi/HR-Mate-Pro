"""
Script to generate sample data for testing all HRMS modules
This will create:
- Attendance records
- Work assignments
- Approval requests
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from random import choice, randint, uniform

sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import Employee
from app.models.attendance import AttendanceDay, AttendanceStatus
from app.models.workflow import (
    WorkAssignment, ApprovalRequest, ApprovalStep, 
    RequestType, ApprovalStatus, ApprovalLevel,
    TaskStatus, TaskPriority
)

def generate_sample_data():
    """Generate sample data for all modules"""
    
    with Session(sync_engine) as session:
        # Get all employees
        employees = session.exec(select(Employee).where(Employee.is_active == True)).all()
        
        if len(employees) < 2:
            print("❌ Need at least 2 employees to generate sample data")
            return
        
        print(f"🎯 Generating sample data for {len(employees)} employees...")
        print("=" * 80)
        
        # Get manager
        manager = session.exec(
            select(Employee).where(Employee.is_manager == True)
        ).first()
        
        if not manager:
            manager = employees[0]
            manager.is_manager = True
            manager.can_approve_leave = True
            manager.can_approve_expenses = True
            session.add(manager)
            session.commit()
        
        # 1. Generate Attendance Records
        print("\n📅 Creating attendance records...")
        attendance_count = 0
        
        for emp in employees:
            for i in range(30):  # Last 30 days
                work_date = date.today() - timedelta(days=i)
                
                # Skip weekends
                if work_date.weekday() >= 5:
                    continue
                
                # Check if attendance already exists
                existing = session.exec(
                    select(AttendanceDay).where(
                        AttendanceDay.employee_id == emp.id,
                        AttendanceDay.date == work_date
                    )
                ).first()
                
                if existing:
                    continue
                
                attendance = AttendanceDay(
                    employee_id=emp.id,
                    date=work_date,
                    check_in=datetime.combine(work_date, datetime.strptime("09:00", "%H:%M").time()),
                    check_out=datetime.combine(work_date, datetime.strptime("18:00", "%H:%M").time()),
                    status=choice([AttendanceStatus.PRESENT, AttendanceStatus.PRESENT, AttendanceStatus.PRESENT, AttendanceStatus.WORK_FROM_HOME]),
                    location_type="office",
                    notes="Auto-generated attendance record"
                )
                session.add(attendance)
                attendance_count += 1
        
        print(f"   ✅ Created {attendance_count} attendance records")
        
        # 2. Generate Work Assignments
        print("\n💼 Creating work assignments...")
        assignment_count = 0
        
        if len(employees) >= 3:
            for i in range(10):  # 10 work assignments
                assignee = choice(employees[2:])  # Assign to non-manager employees
                
                assignment = WorkAssignment(
                    title=f"Task {i+1}: {choice(['Implement feature', 'Fix bug', 'Review PR', 'Update documentation', 'Client meeting'])}",
                    description=f"This is a sample work assignment created for testing purposes. Task {i+1}.",
                    assigner_id=manager.id,
                    assignee_id=assignee.id,
                    priority=choice([TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]),
                    status=choice([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]),
                    due_date=date.today() + timedelta(days=randint(1, 14)),
                    estimated_hours=uniform(2, 40),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(assignment)
                assignment_count += 1
        
        print(f"   ✅ Created {assignment_count} work assignments")
        
        # 3. Generate Approval Requests
        print("\n✅ Creating approval requests...")
        approval_count = 0
        
        # Get the work assignments we just created
        assignments = session.exec(select(WorkAssignment).limit(8)).all()
        
        for assignment in assignments:
            # Create approval request linked to this work assignment
            request_type_value = choice([RequestType.LEAVE, RequestType.EXPENSE, RequestType.TIMESHEET_CORRECTION, RequestType.OVERTIME])
            
            approval = ApprovalRequest(
                entity_type="work_assignment",  # Required field
                entity_id=assignment.id,  # Required field
                requester_id=assignment.assignee_id,
                request_type=request_type_value,
                status=ApprovalStatus.PENDING,
                current_level=1,
                title=f"Approval for: {assignment.title}",
                description=f"Requesting approval for work assignment completion",
                requested_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(approval)
            session.flush()
            
            # Create approval step
            step = ApprovalStep(
                approval_request_id=approval.id,
                level=1,
                approver_id=manager.id,
                approval_role=ApprovalLevel.MANAGER,
                status=ApprovalStatus.PENDING,
                assigned_at=datetime.utcnow()
            )
            session.add(step)
            approval_count += 1
        
        print(f"   ✅ Created {approval_count} approval requests")

        
        # Commit all changes
        session.commit()
        
        print("\n" + "=" * 80)
        print("✅ Sample data generation complete!")
        print("\n📊 Summary:")
        print(f"   - Employees: {len(employees)}")
        print(f"   - Attendance Records: {attendance_count}")
        print(f"   - Work Assignments: {assignment_count}")
        print(f"   - Approval Requests: {approval_count}")
        print("\n💡 You can now test all modules with real data!")

if __name__ == "__main__":
    generate_sample_data()

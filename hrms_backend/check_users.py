"""
Script to check if all users have employee profiles
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import User, Employee

def check_users():
    """Check all users and their employee profiles"""
    
    with Session(sync_engine) as session:
        # Get all users
        users = session.exec(select(User)).all()
        
        print(f"Found {len(users)} users in database:\n")
        print("=" * 80)
        
        for user in users:
            print(f"\n👤 User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role.value}")
            print(f"   Status: {user.status.value}")
            
            # Check for employee profile
            employee = session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if employee:
                print(f"   ✅ Employee Profile Found:")
                print(f"      - Employee ID: {employee.employee_id}")
                print(f"      - Name: {employee.first_name} {employee.last_name}")
                print(f"      - Designation: {employee.designation}")
                print(f"      - Is Manager: {employee.is_manager}")
                print(f"      - Manager ID: {employee.manager_id}")
            else:
                print(f"   ❌ NO EMPLOYEE PROFILE FOUND!")
                print(f"      This will cause 'Employee profile not found' error!")
        
        print("\n" + "=" * 80)
        
        # Count profiles
        total_employees = session.exec(select(Employee)).all()
        print(f"\nSummary:")
        print(f"Total Users: {len(users)}")
        print(f"Total Employee Profiles: {len(total_employees)}")
        print(f"Missing Profiles: {len(users) - len(total_employees)}")

if __name__ == "__main__":
    check_users()

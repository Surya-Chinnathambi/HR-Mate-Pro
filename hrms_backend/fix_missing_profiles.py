"""
Script to create missing employee profiles for users
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import User, Employee, Gender
from datetime import date

def create_missing_profiles():
    """Create employee profiles for users that don't have them"""
    
    with Session(sync_engine) as session:
        # Get all users
        users = session.exec(select(User)).all()
        
        print("Checking for missing employee profiles...\n")
        print("=" * 80)
        
        created_count = 0
        
        for user in users:
            # Check if employee profile exists
            employee = session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                print(f"\n❌ Missing profile for User ID {user.id}: {user.email}")
                print(f"   Creating employee profile...")
                
                # Determine details based on email
                if "surya@example.com" in user.email:
                    first_name = "Surya"
                    last_name = "Admin"
                    designation = "System Administrator"
                    employee_id = "EMP0000"
                elif "manohar.reddy@company.com" in user.email:
                    first_name = "Manohar"
                    last_name = "Reddy"
                    designation = "Engineering Manager"
                    employee_id = "EMP1002"
                else:
                    # Generic employee
                    first_name = user.email.split("@")[0].split(".")[0].title()
                    last_name = user.email.split("@")[0].split(".")[-1].title() if "." in user.email.split("@")[0] else "User"
                    designation = "Employee"
                    employee_id = f"EMP{str(user.id).zfill(4)}"
                
                # Create employee record
                employee = Employee(
                    user_id=user.id,
                    employee_id=employee_id,
                    first_name=first_name,
                    last_name=last_name,
                    display_name=f"{first_name} {last_name}",
                    email=user.email,
                    designation=designation,
                    employment_type="full_time",
                    date_of_joining=date(2024, 1, 1),
                    gender=Gender.OTHER,
                    is_active=True,
                    is_manager=True if user.role.value in ["manager", "admin", "hr"] else False,
                    can_approve_leave=True if user.role.value in ["manager", "admin", "hr"] else False,
                    can_approve_expenses=True if user.role.value in ["manager", "admin", "hr"] else False,
                    can_approve_timesheets=True if user.role.value in ["manager", "admin"] else False,
                    salary=100000.0,
                    currency="USD"
                )
                
                session.add(employee)
                created_count += 1
                
                print(f"   ✅ Created employee profile:")
                print(f"      - Employee ID: {employee_id}")
                print(f"      - Name: {first_name} {last_name}")
                print(f"      - Designation: {designation}")
                print(f"      - Is Manager: {employee.is_manager}")
        
        if created_count > 0:
            session.commit()
            print("\n" + "=" * 80)
            print(f"\n✅ Successfully created {created_count} employee profile(s)!")
        else:
            print("\n" + "=" * 80)
            print(f"\n✅ All users already have employee profiles!")
        
        # Verify
        print("\nFinal verification:")
        users = session.exec(select(User)).all()
        employees = session.exec(select(Employee)).all()
        print(f"Total Users: {len(users)}")
        print(f"Total Employee Profiles: {len(employees)}")
        print(f"Match: {'✅ YES' if len(users) == len(employees) else '❌ NO'}")

if __name__ == "__main__":
    create_missing_profiles()

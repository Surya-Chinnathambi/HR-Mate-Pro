"""
Script to create test users for the HRMS system

Users to create:
1. Febby Thomas (HR Manager) - EMP1001
2. Manohar Reddy (Engineering Manager) - EMP1002
3. Surya Chandra (Senior Software Engineer) - EMP1003
4. Kope Kumar (Software Engineer) - EMP1004
5. Teja Rao (Software Engineer) - EMP1005
6. Srinithy Sharma (Software Engineer) - EMP1006
7. Ashwatha Naik (Junior Software Engineer) - EMP1007
8. Thrisha Menon (Junior Software Engineer) - EMP1008
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import User, Employee, UserRole, UserStatus, Gender, Department, Location
from app.core.security import get_password_hash
from datetime import date, datetime

def create_test_users():
    """Create test users and employees"""
    
    users_data = [
        {
            "email": "febby.thomas@company.com",
            "password": "Febby@2024",
            "employee_id": "EMP1001",
            "first_name": "Febby",
            "last_name": "Thomas",
            "designation": "HR Manager",
            "department": "HR",
            "role": UserRole.ADMIN,
            "is_manager": True,
            "can_approve_leave": True,
            "can_approve_expenses": True
        },
        {
            "email": "manohar.reddy@company.com",
            "password": "Manohar@2024",
            "employee_id": "EMP1002",
            "first_name": "Manohar",
            "last_name": "Reddy",
            "designation": "Engineering Manager",
            "department": "Engineering",
            "role": UserRole.MANAGER,
            "is_manager": True,
            "can_approve_leave": True,
            "can_approve_expenses": True
        },
        {
            "email": "surya.chandra@company.com",
            "password": "Surya@2024",
            "employee_id": "EMP1003",
            "first_name": "Surya",
            "last_name": "Chandra",
            "designation": "Senior Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2  # Will be set to Manohar Reddy
        },
        {
            "email": "kope.kumar@company.com",
            "password": "Kope@2024",
            "employee_id": "EMP1004",
            "first_name": "Kope",
            "last_name": "Kumar",
            "designation": "Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2
        },
        {
            "email": "teja.rao@company.com",
            "password": "Teja@2024",
            "employee_id": "EMP1005",
            "first_name": "Teja",
            "last_name": "Rao",
            "designation": "Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2
        },
        {
            "email": "srinithy.sharma@company.com",
            "password": "Srinithy@2024",
            "employee_id": "EMP1006",
            "first_name": "Srinithy",
            "last_name": "Sharma",
            "designation": "Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2
        },
        {
            "email": "ashwatha.naik@company.com",
            "password": "Ashwatha@2024",
            "employee_id": "EMP1007",
            "first_name": "Ashwatha",
            "last_name": "Naik",
            "designation": "Junior Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2
        },
        {
            "email": "thrisha.menon@company.com",
            "password": "Thrisha@2024",
            "employee_id": "EMP1008",
            "first_name": "Thrisha",
            "last_name": "Menon",
            "designation": "Junior Software Engineer",
            "department": "Engineering",
            "role": UserRole.EMPLOYEE,
            "manager_id": 2
        }
    ]
    
    with Session(sync_engine) as session:
        created_employees = {}
        
        # Create users and employees
        for user_data in users_data:
            # Check if user already exists
            existing_user = session.exec(
                select(User).where(User.email == user_data["email"])
            ).first()
            
            if existing_user:
                print(f"✓ User {user_data['email']} already exists")
                # Get the employee
                existing_emp = session.exec(
                    select(Employee).where(Employee.user_id == existing_user.id)
                ).first()
                if existing_emp:
                    created_employees[user_data["employee_id"]] = existing_emp.id
                continue
            
            # Create user
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                status=UserStatus.ACTIVE
            )
            session.add(user)
            session.flush()  # Get user ID
            
            # Create employee
            employee = Employee(
                user_id=user.id,
                employee_id=user_data["employee_id"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                display_name=f"{user_data['first_name']} {user_data['last_name']}",
                email=user_data["email"],
                designation=user_data["designation"],
                employment_type="full_time",  # String value, not enum
                date_of_joining=date(2024, 1, 1),
                gender=Gender.OTHER,
                is_active=True,
                is_manager=user_data.get("is_manager", False),
                can_approve_leave=user_data.get("can_approve_leave", False),
                can_approve_expenses=user_data.get("can_approve_expenses", False),
                can_approve_timesheets=user_data.get("can_approve_timesheets", False),
                salary=100000.0,
                currency="USD"
            )
            
            session.add(employee)
            session.flush()
            
            created_employees[user_data["employee_id"]] = employee.id
            
            print(f"✓ Created user: {user_data['email']} ({user_data['employee_id']})")
        
        # Update manager relationships
        for user_data in users_data:
            if "manager_id" in user_data:
                manager_emp_id = created_employees.get("EMP1002")  # Manohar is the manager
                emp_id = created_employees.get(user_data["employee_id"])
                
                if manager_emp_id and emp_id:
                    employee = session.get(Employee, emp_id)
                    if employee:
                        employee.manager_id = manager_emp_id
                        session.add(employee)
                        print(f"  → Set manager for {user_data['employee_id']}")
        
        session.commit()
        print("\n✅ All test users created successfully!")
        print("\n📋 Login Credentials:")
        print("=" * 60)
        for user_data in users_data:
            print(f"{user_data['first_name']} {user_data['last_name']} ({user_data['employee_id']})")
            print(f"  Email: {user_data['email']}")
            print(f"  Password: {user_data['password']}")
            print(f"  Role: {user_data['role'].value}")
            print()

if __name__ == "__main__":
    create_test_users()

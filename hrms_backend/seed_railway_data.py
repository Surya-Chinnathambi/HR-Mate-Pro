"""
Seed Railway PostgreSQL with sample HRMS data
Generates 25 employees with complete data
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, date, timedelta, time
from random import choice, randint, uniform, random, seed as random_seed
from typing import List
import bcrypt

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import (
    User, Employee, Department, Location, 
    UserRole, UserStatus, Gender
)
from app.models.attendance import (
    AttendanceDay, AttendanceStatus, AttendanceSource,
    LeaveType, LeaveBalance, LeaveApplication, LeaveApplicationStatus,
    Holiday
)
from app.models.extras import Payroll, Notification, NotificationPriority

# Set seed for reproducibility
random_seed(42)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Sample employee data
EMPLOYEES_DATA = [
    # HR Team (2)
    {"first_name": "Sarah", "last_name": "Johnson", "email": "sarah.johnson@company.com", "designation": "HR Manager", "role": "hr", "is_manager": True, "dept": "Human Resources"},
    {"first_name": "Michael", "last_name": "Chen", "email": "michael.chen@company.com", "designation": "HR Executive", "role": "hr", "is_manager": False, "dept": "Human Resources"},
    
    # Managers (3)
    {"first_name": "Emily", "last_name": "Davis", "email": "emily.davis@company.com", "designation": "Engineering Manager", "role": "manager", "is_manager": True, "dept": "Engineering", "team": 1},
    {"first_name": "David", "last_name": "Wilson", "email": "david.wilson@company.com", "designation": "Product Manager", "role": "manager", "is_manager": True, "dept": "Product", "team": 2},
    {"first_name": "Jessica", "last_name": "Martinez", "email": "jessica.martinez@company.com", "designation": "Sales Manager", "role": "manager", "is_manager": True, "dept": "Sales", "team": 3},
    
    # Engineering Team (7)
    {"first_name": "James", "last_name": "Anderson", "email": "james.anderson@company.com", "designation": "Senior Software Engineer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Robert", "last_name": "Taylor", "email": "robert.taylor@company.com", "designation": "Software Engineer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Linda", "last_name": "Thomas", "email": "linda.thomas@company.com", "designation": "Frontend Developer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Christopher", "last_name": "Jackson", "email": "christopher.jackson@company.com", "designation": "Backend Developer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Patricia", "last_name": "White", "email": "patricia.white@company.com", "designation": "DevOps Engineer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Daniel", "last_name": "Harris", "email": "daniel.harris@company.com", "designation": "QA Engineer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    {"first_name": "Nancy", "last_name": "Martin", "email": "nancy.martin@company.com", "designation": "Software Engineer", "role": "employee", "dept": "Engineering", "team": 1, "manager_idx": 2},
    
    # Product Team (6)
    {"first_name": "Matthew", "last_name": "Thompson", "email": "matthew.thompson@company.com", "designation": "Product Owner", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    {"first_name": "Jennifer", "last_name": "Garcia", "email": "jennifer.garcia@company.com", "designation": "Product Designer", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    {"first_name": "Anthony", "last_name": "Martinez", "email": "anthony.martinez@company.com", "designation": "UX Researcher", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    {"first_name": "Lisa", "last_name": "Robinson", "email": "lisa.robinson@company.com", "designation": "Product Analyst", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    {"first_name": "Mark", "last_name": "Clark", "email": "mark.clark@company.com", "designation": "Business Analyst", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    {"first_name": "Sandra", "last_name": "Rodriguez", "email": "sandra.rodriguez@company.com", "designation": "Product Designer", "role": "employee", "dept": "Product", "team": 2, "manager_idx": 3},
    
    # Sales Team (7)
    {"first_name": "Steven", "last_name": "Lewis", "email": "steven.lewis@company.com", "designation": "Senior Sales Executive", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "Karen", "last_name": "Lee", "email": "karen.lee@company.com", "designation": "Sales Executive", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "Paul", "last_name": "Walker", "email": "paul.walker@company.com", "designation": "Account Manager", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "Betty", "last_name": "Hall", "email": "betty.hall@company.com", "designation": "Sales Executive", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "Donald", "last_name": "Allen", "email": "donald.allen@company.com", "designation": "Business Development", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "Helen", "last_name": "Young", "email": "helen.young@company.com", "designation": "Sales Coordinator", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
    {"first_name": "George", "last_name": "King", "email": "george.king@company.com", "designation": "Sales Executive", "role": "employee", "dept": "Sales", "team": 3, "manager_idx": 4},
]

def create_departments_and_locations(session: Session):
    """Create departments and locations"""
    print("Creating departments and locations...")
    
    # Create locations
    locations_data = [
        {"name": "Headquarters", "city": "San Francisco", "country": "USA", "timezone": "America/Los_Angeles"},
        {"name": "Tech Hub", "city": "Bangalore", "country": "India", "timezone": "Asia/Kolkata"},
        {"name": "Sales Office", "city": "New York", "country": "USA", "timezone": "America/New_York"},
    ]
    
    locations = []
    for loc_data in locations_data:
        location = Location(
            name=loc_data["name"],
            city=loc_data["city"],
            country=loc_data["country"],
            timezone=loc_data["timezone"],
            address=f"{loc_data['city']}, {loc_data['country']}"
        )
        session.add(location)
        locations.append(location)
    
    session.commit()
    print(f"✅ Created {len(locations)} locations")
    
    # Create departments
    departments_data = [
        {"name": "Human Resources", "code": "HR"},
        {"name": "Engineering", "code": "ENG"},
        {"name": "Product", "code": "PRD"},
        {"name": "Sales", "code": "SAL"},
        {"name": "Marketing", "code": "MKT"},
    ]
    
    departments = []
    for dept_data in departments_data:
        department = Department(
            name=dept_data["name"],
            code=dept_data["code"],
            description=f"{dept_data['name']} Department"
        )
        session.add(department)
        departments.append(department)
    
    session.commit()
    print(f"✅ Created {len(departments)} departments")
    
    return locations, departments

def create_leave_types(session: Session):
    """Create leave types"""
    print("Creating leave types...")
    
    leave_types_data = [
        {"name": "Casual Leave", "code": "CL", "days": 12, "is_paid": True},
        {"name": "Sick Leave", "code": "SL", "days": 12, "is_paid": True},
        {"name": "Earned Leave", "code": "EL", "days": 15, "is_paid": True},
        {"name": "Unpaid Leave", "code": "UL", "days": 0, "is_paid": False},
    ]
    
    leave_types = []
    for lt_data in leave_types_data:
        leave_type = LeaveType(
            name=lt_data["name"],
            code=lt_data["code"],
            default_days_per_year=lt_data["days"],
            is_paid=lt_data["is_paid"],
            requires_approval=True,
            can_be_carried_forward=lt_data["code"] == "EL",
            min_days_notice=1,
            is_active=True
        )
        session.add(leave_type)
        leave_types.append(leave_type)
    
    session.commit()
    print(f"✅ Created {len(leave_types)} leave types")
    
    return leave_types

def create_users_and_employees(session: Session, departments: List[Department], locations: List[Location]):
    """Create users and employees"""
    print("\nCreating users and employees...")
    
    users = []
    employees = []
    
    # Get department and location mappings
    dept_map = {d.name: d for d in departments}
    main_location = locations[0]
    
    for idx, emp_data in enumerate(EMPLOYEES_DATA, start=1):
        # Create user
        user = User(
            email=emp_data["email"],
            hashed_password=hash_password("password123"),  # Default password
            role=UserRole.ADMIN if emp_data["role"] == "hr" else UserRole.EMPLOYEE,
            status=UserStatus.ACTIVE
        )
        session.add(user)
        session.flush()  # Get user ID
        
        # Create employee
        department = dept_map.get(emp_data["dept"])
        
        employee = Employee(
            user_id=user.id,
            employee_id=f"EMP{idx:04d}",
            first_name=emp_data["first_name"],
            last_name=emp_data["last_name"],
            display_name=f"{emp_data['first_name']} {emp_data['last_name']}",
            email=emp_data["email"],
            phone=f"+1-555-{randint(1000, 9999)}",
            date_of_birth=date(1985 + randint(0, 15), randint(1, 12), randint(1, 28)),
            gender=choice([Gender.MALE, Gender.FEMALE]),
            date_of_joining=date(2020 + randint(0, 4), randint(1, 12), randint(1, 28)),
            designation=emp_data["designation"],
            employment_type="Full-time",
            department_id=department.id if department else None,
            location_id=main_location.id,
            salary=50000 + randint(0, 100000),
            currency="USD",
            is_active=True,
            role=emp_data["role"],
            team_id=emp_data.get("team"),
            is_manager=emp_data.get("is_manager", False),
            can_approve_leave=emp_data.get("is_manager", False),
            can_approve_expenses=emp_data.get("is_manager", False),
            can_approve_timesheets=emp_data.get("is_manager", False),
            current_workload_hours=0.0,
            max_workload_hours=40.0
        )
        session.add(employee)
        employees.append(employee)
        users.append(user)
    
    session.commit()
    print(f"✅ Created {len(users)} users and {len(employees)} employees")
    
    # Set manager relationships
    for idx, emp_data in enumerate(EMPLOYEES_DATA):
        if "manager_idx" in emp_data:
            employee = employees[idx]
            manager = employees[emp_data["manager_idx"]]
            employee.manager_id = manager.id
            employee.reporting_manager_id = manager.id
            session.add(employee)
    
    session.commit()
    print("✅ Set manager relationships")
    
    return users, employees

def create_leave_balances(session: Session, employees: List[Employee], leave_types: List[LeaveType]):
    """Create leave balances for all employees"""
    print("\nCreating leave balances...")
    
    current_year = datetime.now().year
    count = 0
    
    for employee in employees:
        for leave_type in leave_types:
            if leave_type.is_paid:
                balance = LeaveBalance(
                    employee_id=employee.id,
                    leave_type_id=leave_type.id,
                    year=current_year,
                    opening_balance=leave_type.default_days_per_year,
                    accrued=leave_type.default_days_per_year,
                    consumed=randint(0, 5),
                    balance=leave_type.default_days_per_year - randint(0, 5),
                    pending=0,
                    carried_forward=0,
                    encashed=0
                )
                session.add(balance)
                count += 1
    
    session.commit()
    print(f"✅ Created {count} leave balances")

def create_attendance_records(session: Session, employees: List[Employee]):
    """Create attendance records for last 30 days"""
    print("\nCreating attendance records...")
    
    count = 0
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    for employee in employees:
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                status = choice([
                    AttendanceStatus.PRESENT,
                    AttendanceStatus.PRESENT,
                    AttendanceStatus.PRESENT,
                    AttendanceStatus.PRESENT,
                    AttendanceStatus.WORK_FROM_HOME,
                ])
                
                if status == AttendanceStatus.PRESENT or status == AttendanceStatus.WORK_FROM_HOME:
                    attendance = AttendanceDay(
                        employee_id=employee.id,
                        date=current_date,
                        status=status,
                        check_in=time(9, randint(0, 30)),
                        check_out=time(17 + randint(0, 2), randint(0, 59)),
                        work_hours=8.0 + uniform(-0.5, 1.5),
                        overtime_minutes=0,
                        source=AttendanceSource.WEB,
                        location_type="office" if status == AttendanceStatus.PRESENT else "remote",
                        is_regularized=False
                    )
                    session.add(attendance)
                    count += 1
            
            current_date += timedelta(days=1)
    
    session.commit()
    print(f"✅ Created {count} attendance records")

def create_sample_payrolls(session: Session, employees: List[Employee]):
    """Create payroll records for last 3 months"""
    print("\nCreating payroll records...")
    
    count = 0
    current_date = date.today()
    
    for month_offset in range(3):
        month = current_date.month - month_offset
        year = current_date.year
        
        if month <= 0:
            month += 12
            year -= 1
        
        for employee in employees:
            basic = employee.salary * 0.50
            hra = employee.salary * 0.20
            special = employee.salary * 0.20
            transport = 2000
            medical = 1500
            
            gross = basic + hra + special + transport + medical
            
            pf = gross * 0.12
            tax = gross * 0.10 if gross > 50000 else 0
            pt = 200
            
            total_ded = pf + tax + pt
            net = gross - total_ded
            
            payroll = Payroll(
                employee_id=employee.id,
                month=month,
                year=year,
                period=f"{year}-{month:02d}",
                basic_salary=basic,
                hra=hra,
                special_allowance=special,
                transport_allowance=transport,
                medical_allowance=medical,
                other_allowances=0,
                gross_salary=gross,
                pf_employee=pf,
                pf_employer=pf,
                income_tax=tax,
                professional_tax=pt,
                other_deductions=0,
                total_deductions=total_ded,
                net_salary=net,
                payment_mode="Bank Transfer",
                status="paid"
            )
            session.add(payroll)
            count += 1
    
    session.commit()
    print(f"✅ Created {count} payroll records")

def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 RAILWAY DATABASE SEEDING STARTED")
    print("=" * 60)
    
    session = Session(sync_engine)
    
    try:
        # Check if data already exists
        existing_users = session.exec(select(User)).all()
        if existing_users:
            print(f"\n⚠️  Warning: Found {len(existing_users)} existing users")
            response = input("Do you want to continue? This will add more data. (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted")
                return
        
        # Create base data
        locations, departments = create_departments_and_locations(session)
        leave_types = create_leave_types(session)
        
        # Create users and employees
        users, employees = create_users_and_employees(session, departments, locations)
        
        # Create related data
        create_leave_balances(session, employees, leave_types)
        create_attendance_records(session, employees)
        create_sample_payrolls(session, employees)
        
        print("\n" + "=" * 60)
        print("✅ SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Users: {len(users)}")
        print(f"   Employees: {len(employees)}")
        print(f"   Departments: {len(departments)}")
        print(f"   Locations: {len(locations)}")
        print(f"   Leave Types: {len(leave_types)}")
        print(f"\n🔑 Login Credentials:")
        print(f"   Email: sarah.johnson@company.com (HR)")
        print(f"   Email: emily.davis@company.com (Manager)")
        print(f"   Email: james.anderson@company.com (Employee)")
        print(f"   Password: password123 (for all users)")
        print("=" * 60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()

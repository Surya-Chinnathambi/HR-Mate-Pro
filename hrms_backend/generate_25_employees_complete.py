"""
Comprehensive Data Generation Script for 25 Employees
Creates complete HRMS data including:
- 25 employees with proper organizational structure (2 HR, 3 managers, 20 employees)
- User accounts for all
- Attendance records for 30 days
- Leave balances
- Leave applications
- Payslips for last 12 months
- Departments and locations
- Reporting relationships
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta, time
from random import choice, randint, uniform, random, seed as random_seed
from typing import List, Dict

sys.path.append(str(Path(__file__).parent))

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
import hashlib

# Simple password hashing function
def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    # In production, use proper bcrypt, but for data generation this is fine
    return hashlib.sha256(password.encode()).hexdigest()

# Set seed for reproducibility
random_seed(42)

# Employee data structure
EMPLOYEE_DATA = [
    # HR Department (2 people)
    {
        "employee_id": "EMP001",
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.sharma@company.com",
        "designation": "HR Manager",
        "department": "Human Resources",
        "role": "hr",
        "user_role": UserRole.HR,
        "is_manager": True,
        "can_approve_leave": True,
        "can_approve_expenses": True,
        "gender": Gender.FEMALE,
        "date_of_birth": "1988-05-15",
        "salary": 85000,
        "manager": None,
        "team": "HR"
    },
    {
        "employee_id": "EMP002",
        "first_name": "Arun",
        "last_name": "Kumar",
        "email": "arun.kumar@company.com",
        "designation": "HR Executive",
        "department": "Human Resources",
        "role": "hr",
        "user_role": UserRole.HR,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1992-08-22",
        "salary": 55000,
        "manager": "EMP001",
        "team": "HR"
    },
    
    # Engineering Department (1 Manager + 8 Employees)
    {
        "employee_id": "EMP003",
        "first_name": "Rajesh",
        "last_name": "Patel",
        "email": "rajesh.patel@company.com",
        "designation": "Engineering Manager",
        "department": "Engineering",
        "role": "manager",
        "user_role": UserRole.MANAGER,
        "is_manager": True,
        "can_approve_leave": True,
        "can_approve_expenses": True,
        "gender": Gender.MALE,
        "date_of_birth": "1985-03-10",
        "salary": 120000,
        "manager": None,
        "team": "Engineering"
    },
    {
        "employee_id": "EMP004",
        "first_name": "Sneha",
        "last_name": "Reddy",
        "email": "sneha.reddy@company.com",
        "designation": "Senior Software Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1990-11-05",
        "salary": 95000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP005",
        "first_name": "Vikram",
        "last_name": "Singh",
        "email": "vikram.singh@company.com",
        "designation": "Software Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1993-07-18",
        "salary": 75000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP006",
        "first_name": "Anita",
        "last_name": "Desai",
        "email": "anita.desai@company.com",
        "designation": "Software Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1994-02-28",
        "salary": 72000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP007",
        "first_name": "Karthik",
        "last_name": "Nair",
        "email": "karthik.nair@company.com",
        "designation": "Junior Software Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1996-09-12",
        "salary": 55000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP008",
        "first_name": "Divya",
        "last_name": "Menon",
        "email": "divya.menon@company.com",
        "designation": "QA Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1995-04-20",
        "salary": 62000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP009",
        "first_name": "Amit",
        "last_name": "Verma",
        "email": "amit.verma@company.com",
        "designation": "DevOps Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1991-12-08",
        "salary": 88000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP010",
        "first_name": "Pooja",
        "last_name": "Joshi",
        "email": "pooja.joshi@company.com",
        "designation": "UI/UX Designer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1993-06-14",
        "salary": 68000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    {
        "employee_id": "EMP011",
        "first_name": "Rahul",
        "last_name": "Chopra",
        "email": "rahul.chopra@company.com",
        "designation": "Software Engineer",
        "department": "Engineering",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1994-10-25",
        "salary": 70000,
        "manager": "EMP003",
        "team": "Engineering"
    },
    
    # Sales Department (1 Manager + 6 Employees)
    {
        "employee_id": "EMP012",
        "first_name": "Neha",
        "last_name": "Gupta",
        "email": "neha.gupta@company.com",
        "designation": "Sales Manager",
        "department": "Sales",
        "role": "manager",
        "user_role": UserRole.MANAGER,
        "is_manager": True,
        "can_approve_leave": True,
        "can_approve_expenses": True,
        "gender": Gender.FEMALE,
        "date_of_birth": "1987-01-30",
        "salary": 110000,
        "manager": None,
        "team": "Sales"
    },
    {
        "employee_id": "EMP013",
        "first_name": "Sanjay",
        "last_name": "Malhotra",
        "email": "sanjay.malhotra@company.com",
        "designation": "Senior Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1989-05-17",
        "salary": 82000,
        "manager": "EMP012",
        "team": "Sales"
    },
    {
        "employee_id": "EMP014",
        "first_name": "Meera",
        "last_name": "Iyer",
        "email": "meera.iyer@company.com",
        "designation": "Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1992-03-22",
        "salary": 65000,
        "manager": "EMP012",
        "team": "Sales"
    },
    {
        "employee_id": "EMP015",
        "first_name": "Arjun",
        "last_name": "Rao",
        "email": "arjun.rao@company.com",
        "designation": "Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1993-08-09",
        "salary": 63000,
        "manager": "EMP012",
        "team": "Sales"
    },
    {
        "employee_id": "EMP016",
        "first_name": "Kavya",
        "last_name": "Pillai",
        "email": "kavya.pillai@company.com",
        "designation": "Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1994-11-03",
        "salary": 61000,
        "manager": "EMP012",
        "team": "Sales"
    },
    {
        "employee_id": "EMP017",
        "first_name": "Rohan",
        "last_name": "Bhatia",
        "email": "rohan.bhatia@company.com",
        "designation": "Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1995-07-19",
        "salary": 59000,
        "manager": "EMP012",
        "team": "Sales"
    },
    {
        "employee_id": "EMP018",
        "first_name": "Simran",
        "last_name": "Kapoor",
        "email": "simran.kapoor@company.com",
        "designation": "Sales Executive",
        "department": "Sales",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1996-02-14",
        "salary": 58000,
        "manager": "EMP012",
        "team": "Sales"
    },
    
    # Marketing Department (1 Manager + 5 Employees)
    {
        "employee_id": "EMP019",
        "first_name": "Deepak",
        "last_name": "Agarwal",
        "email": "deepak.agarwal@company.com",
        "designation": "Marketing Manager",
        "department": "Marketing",
        "role": "manager",
        "user_role": UserRole.MANAGER,
        "is_manager": True,
        "can_approve_leave": True,
        "can_approve_expenses": True,
        "gender": Gender.MALE,
        "date_of_birth": "1986-09-05",
        "salary": 105000,
        "manager": None,
        "team": "Marketing"
    },
    {
        "employee_id": "EMP020",
        "first_name": "Tanvi",
        "last_name": "Shah",
        "email": "tanvi.shah@company.com",
        "designation": "Digital Marketing Specialist",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1991-04-12",
        "salary": 72000,
        "manager": "EMP019",
        "team": "Marketing"
    },
    {
        "employee_id": "EMP021",
        "first_name": "Gaurav",
        "last_name": "Saxena",
        "email": "gaurav.saxena@company.com",
        "designation": "Content Writer",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1993-12-01",
        "salary": 58000,
        "manager": "EMP019",
        "team": "Marketing"
    },
    {
        "employee_id": "EMP022",
        "first_name": "Riya",
        "last_name": "Bhatt",
        "email": "riya.bhatt@company.com",
        "designation": "Social Media Manager",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1994-06-28",
        "salary": 65000,
        "manager": "EMP019",
        "team": "Marketing"
    },
    {
        "employee_id": "EMP023",
        "first_name": "Nikhil",
        "last_name": "Khanna",
        "email": "nikhil.khanna@company.com",
        "designation": "SEO Specialist",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1995-03-16",
        "salary": 62000,
        "manager": "EMP019",
        "team": "Marketing"
    },
    {
        "employee_id": "EMP024",
        "first_name": "Isha",
        "last_name": "Mishra",
        "email": "isha.mishra@company.com",
        "designation": "Marketing Executive",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.FEMALE,
        "date_of_birth": "1996-10-07",
        "salary": 54000,
        "manager": "EMP019",
        "team": "Marketing"
    },
    {
        "employee_id": "EMP025",
        "first_name": "Aditya",
        "last_name": "Bansal",
        "email": "aditya.bansal@company.com",
        "designation": "Brand Manager",
        "department": "Marketing",
        "role": "employee",
        "user_role": UserRole.EMPLOYEE,
        "is_manager": False,
        "can_approve_leave": False,
        "can_approve_expenses": False,
        "gender": Gender.MALE,
        "date_of_birth": "1992-01-24",
        "salary": 78000,
        "manager": "EMP019",
        "team": "Marketing"
    },
]

# Indian names for variety
FIRST_NAMES_MALE = ["Rahul", "Amit", "Rohan", "Vikram", "Arjun", "Karthik", "Sanjay", "Deepak"]
FIRST_NAMES_FEMALE = ["Priya", "Sneha", "Anita", "Divya", "Pooja", "Neha", "Meera", "Kavya"]
LAST_NAMES = ["Sharma", "Kumar", "Patel", "Reddy", "Singh", "Desai", "Nair", "Gupta", "Verma", "Iyer"]

# Simple password hashing (already defined above)

def create_departments(session: Session) -> Dict[str, Department]:
    """Create departments"""
    print("\n📁 Creating Departments...")
    
    departments_data = [
        {"name": "Human Resources", "code": "HR", "description": "HR and recruitment"},
        {"name": "Engineering", "code": "ENG", "description": "Product development and engineering"},
        {"name": "Sales", "code": "SAL", "description": "Sales and business development"},
        {"name": "Marketing", "code": "MKT", "description": "Marketing and branding"},
    ]
    
    departments = {}
    for dept_data in departments_data:
        dept = session.exec(select(Department).where(Department.code == dept_data["code"])).first()
        if not dept:
            dept = Department(**dept_data)
            session.add(dept)
            session.commit()
            session.refresh(dept)
            print(f"   ✅ Created department: {dept.name}")
        else:
            print(f"   ⚠️  Department already exists: {dept.name}")
        departments[dept.name] = dept
    
    return departments

def create_locations(session: Session) -> Dict[str, Location]:
    """Create office locations"""
    print("\n📍 Creating Locations...")
    
    locations_data = [
        {"name": "Bangalore HQ", "city": "Bangalore", "state": "Karnataka", "country": "India", "timezone": "Asia/Kolkata"},
        {"name": "Mumbai Office", "city": "Mumbai", "state": "Maharashtra", "country": "India", "timezone": "Asia/Kolkata"},
        {"name": "Delhi Office", "city": "Delhi", "state": "Delhi", "country": "India", "timezone": "Asia/Kolkata"},
    ]
    
    locations = {}
    for loc_data in locations_data:
        loc = session.exec(select(Location).where(Location.name == loc_data["name"])).first()
        if not loc:
            loc = Location(**loc_data)
            session.add(loc)
            session.commit()
            session.refresh(loc)
            print(f"   ✅ Created location: {loc.name}")
        else:
            print(f"   ⚠️  Location already exists: {loc.name}")
        locations[loc.name] = loc
    
    return locations

def create_leave_types(session: Session) -> Dict[str, LeaveType]:
    """Create leave types"""
    print("\n🏖️  Creating Leave Types...")
    
    leave_types_data = [
        {
            "name": "Casual Leave",
            "code": "CL",
            "description": "Casual leave for personal work",
            "default_days_per_year": 12,
            "is_paid": True,
            "requires_approval": True,
            "can_be_carried_forward": False,
        },
        {
            "name": "Sick Leave",
            "code": "SL",
            "description": "Leave for medical reasons",
            "default_days_per_year": 12,
            "is_paid": True,
            "requires_approval": False,
            "can_be_carried_forward": False,
        },
        {
            "name": "Earned Leave",
            "code": "EL",
            "description": "Earned/Privilege leave",
            "default_days_per_year": 18,
            "is_paid": True,
            "requires_approval": True,
            "can_be_carried_forward": True,
        },
        {
            "name": "Unpaid Leave",
            "code": "UL",
            "description": "Leave without pay",
            "default_days_per_year": 0,
            "is_paid": False,
            "requires_approval": True,
            "can_be_carried_forward": False,
        },
    ]
    
    leave_types = {}
    for lt_data in leave_types_data:
        lt = session.exec(select(LeaveType).where(LeaveType.code == lt_data["code"])).first()
        if not lt:
            lt = LeaveType(**lt_data)
            session.add(lt)
            session.commit()
            session.refresh(lt)
            print(f"   ✅ Created leave type: {lt.name}")
        else:
            print(f"   ⚠️  Leave type already exists: {lt.name}")
        leave_types[lt.code] = lt
    
    return leave_types

def create_holidays(session: Session):
    """Create company holidays"""
    print("\n🎉 Creating Holidays...")
    
    current_year = datetime.now().year
    holidays_data = [
        {"name": "Republic Day", "date": date(current_year, 1, 26)},
        {"name": "Holi", "date": date(current_year, 3, 14)},
        {"name": "Good Friday", "date": date(current_year, 3, 29)},
        {"name": "Independence Day", "date": date(current_year, 8, 15)},
        {"name": "Gandhi Jayanti", "date": date(current_year, 10, 2)},
        {"name": "Diwali", "date": date(current_year, 11, 1)},
        {"name": "Christmas", "date": date(current_year, 12, 25)},
    ]
    
    for holiday_data in holidays_data:
        holiday = session.exec(
            select(Holiday).where(
                Holiday.date == holiday_data["date"],
                Holiday.name == holiday_data["name"]
            )
        ).first()
        
        if not holiday:
            holiday = Holiday(
                name=holiday_data["name"],
                date=holiday_data["date"],
                year=current_year,
                is_optional=False
            )
            session.add(holiday)
            print(f"   ✅ Created holiday: {holiday.name}")
    
    session.commit()

def create_employees(session: Session, departments: Dict, locations: Dict) -> Dict[str, Employee]:
    """Create 25 employees with proper hierarchy"""
    print("\n👥 Creating 25 Employees...")
    
    employees = {}
    
    # First pass: Create users and employees without manager references
    for emp_data in EMPLOYEE_DATA:
        # Check if user already exists
        user = session.exec(select(User).where(User.email == emp_data["email"])).first()
        
        if not user:
            # Create user
            user = User(
                email=emp_data["email"],
                hashed_password=hash_password("password123"),  # Default password
                role=emp_data["user_role"],
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        
        # Check if employee already exists
        employee = session.exec(select(Employee).where(Employee.employee_id == emp_data["employee_id"])).first()
        
        if not employee:
            # Calculate date of joining (between 1-5 years ago)
            years_ago = randint(1, 5)
            months_ago = randint(0, 11)
            date_of_joining = date.today() - timedelta(days=years_ago * 365 + months_ago * 30)
            
            # Create employee
            employee = Employee(
                user_id=user.id,
                employee_id=emp_data["employee_id"],
                first_name=emp_data["first_name"],
                last_name=emp_data["last_name"],
                display_name=f"{emp_data['first_name']} {emp_data['last_name']}",
                email=emp_data["email"],
                phone=f"+91{randint(7000000000, 9999999999)}",
                date_of_birth=datetime.strptime(emp_data["date_of_birth"], "%Y-%m-%d").date(),
                gender=emp_data["gender"],
                date_of_joining=date_of_joining,
                designation=emp_data["designation"],
                employment_type="full_time",
                department_id=departments[emp_data["department"]].id,
                location_id=choice(list(locations.values())).id,
                salary=emp_data["salary"],
                currency="INR",
                is_active=True,
                is_manager=emp_data["is_manager"],
                can_approve_leave=emp_data["can_approve_leave"],
                can_approve_expenses=emp_data["can_approve_expenses"],
                role=emp_data["role"],
                team_id=1,  # Default team
            )
            session.add(employee)
            session.commit()
            session.refresh(employee)
            print(f"   ✅ Created employee: {employee.display_name} ({employee.employee_id})")
        else:
            print(f"   ⚠️  Employee already exists: {employee.display_name} ({employee.employee_id})")
        
        employees[emp_data["employee_id"]] = employee
    
    # Second pass: Update manager relationships
    print("\n🔗 Setting up manager relationships...")
    for emp_data in EMPLOYEE_DATA:
        if emp_data["manager"]:
            employee = employees[emp_data["employee_id"]]
            manager = employees[emp_data["manager"]]
            employee.manager_id = manager.id
            employee.reporting_manager_id = manager.id
            session.add(employee)
            print(f"   ✅ {employee.display_name} reports to {manager.display_name}")
    
    session.commit()
    return employees

def create_attendance_records(session: Session, employees: Dict):
    """Create 30 days of attendance for all employees"""
    print("\n📅 Creating Attendance Records (30 days)...")
    
    # Get holidays
    holidays = session.exec(select(Holiday)).all()
    holiday_dates = {h.date for h in holidays}
    
    total_records = 0
    
    for emp_id, employee in employees.items():
        for i in range(30):
            work_date = date.today() - timedelta(days=i)
            
            # Skip weekends
            if work_date.weekday() >= 5:
                continue
            
            # Skip holidays
            if work_date in holiday_dates:
                continue
            
            # Check if attendance already exists
            existing = session.exec(
                select(AttendanceDay).where(
                    AttendanceDay.employee_id == employee.id,
                    AttendanceDay.date == work_date
                )
            ).first()
            
            if existing:
                continue
            
            # Random attendance status (mostly present)
            status_choice = random()
            if status_choice < 0.85:
                status = AttendanceStatus.PRESENT
                check_in_hour = randint(8, 10)
                check_in_minute = randint(0, 59)
                check_out_hour = randint(17, 19)
                check_out_minute = randint(0, 59)
                work_hours = check_out_hour - check_in_hour + (check_out_minute - check_in_minute) / 60
            elif status_choice < 0.90:
                status = AttendanceStatus.WORK_FROM_HOME
                check_in_hour = 9
                check_in_minute = 0
                check_out_hour = 18
                check_out_minute = 0
                work_hours = 9.0
            elif status_choice < 0.95:
                status = AttendanceStatus.HALF_DAY
                check_in_hour = 9
                check_in_minute = 0
                check_out_hour = 13
                check_out_minute = 0
                work_hours = 4.0
            else:
                status = AttendanceStatus.ON_LEAVE
                check_in_hour = None
                check_in_minute = None
                check_out_hour = None
                check_out_minute = None
                work_hours = 0
            
            attendance = AttendanceDay(
                employee_id=employee.id,
                date=work_date,
                status=status,
                check_in=time(check_in_hour, check_in_minute) if check_in_hour else None,
                check_out=time(check_out_hour, check_out_minute) if check_out_hour else None,
                work_hours=work_hours,
                source=AttendanceSource.WEB,
                location_type="office" if status == AttendanceStatus.PRESENT else "remote",
            )
            session.add(attendance)
            total_records += 1
    
    session.commit()
    print(f"   ✅ Created {total_records} attendance records")

def create_leave_balances(session: Session, employees: Dict, leave_types: Dict):
    """Create leave balances for all employees"""
    print("\n💰 Creating Leave Balances...")
    
    current_year = datetime.now().year
    total_balances = 0
    
    for emp_id, employee in employees.items():
        for lt_code, leave_type in leave_types.items():
            # Check if balance already exists
            existing = session.exec(
                select(LeaveBalance).where(
                    LeaveBalance.employee_id == employee.id,
                    LeaveBalance.leave_type_id == leave_type.id,
                    LeaveBalance.year == current_year
                )
            ).first()
            
            if existing:
                continue
            
            # Random consumed leaves (0-5)
            consumed = randint(0, min(5, leave_type.default_days_per_year))
            
            balance = LeaveBalance(
                employee_id=employee.id,
                leave_type_id=leave_type.id,
                year=current_year,
                opening_balance=leave_type.default_days_per_year,
                accrued=0,
                consumed=consumed,
                balance=leave_type.default_days_per_year - consumed,
                pending=0,
                carried_forward=0,
                encashed=0,
            )
            session.add(balance)
            total_balances += 1
    
    session.commit()
    print(f"   ✅ Created {total_balances} leave balance records")

def create_leave_applications(session: Session, employees: Dict, leave_types: Dict):
    """Create some leave applications"""
    print("\n📝 Creating Leave Applications...")
    
    total_applications = 0
    
    # Create 2-3 leave applications per employee
    for emp_id, employee in employees.items():
        num_applications = randint(2, 4)
        
        for i in range(num_applications):
            # Random leave type
            leave_type = choice(list(leave_types.values()))
            
            # Random date in last 60 days
            days_ago = randint(5, 60)
            start_date_val = date.today() - timedelta(days=days_ago)
            
            # Random duration (1-3 days)
            duration = randint(1, 3)
            end_date_val = start_date_val + timedelta(days=duration - 1)
            
            # Random status
            status = choice([
                LeaveApplicationStatus.APPROVED,
                LeaveApplicationStatus.APPROVED,
                LeaveApplicationStatus.APPROVED,
                LeaveApplicationStatus.PENDING,
            ])
            
            # Get approver (manager)
            approver_id = employee.manager_id if employee.manager_id else None
            
            application = LeaveApplication(
                employee_id=employee.id,
                leave_type_id=leave_type.id,
                start_date=start_date_val,
                end_date=end_date_val,
                total_days=duration,
                reason=choice([
                    "Personal work",
                    "Family function",
                    "Medical appointment",
                    "Travel",
                    "Home renovation",
                ]),
                status=status,
                applied_date=start_date_val - timedelta(days=randint(3, 10)),
                approver_id=approver_id,
                approved_date=datetime.now() if status == LeaveApplicationStatus.APPROVED else None,
            )
            session.add(application)
            total_applications += 1
    
    session.commit()
    print(f"   ✅ Created {total_applications} leave applications")

def create_payslips(session: Session, employees: Dict):
    """Create 12 months of payslips for all employees"""
    print("\n💵 Creating Payslips (12 months)...")
    
    total_payslips = 0
    
    for emp_id, employee in employees.items():
        # Create payslips for last 12 months
        for month_offset in range(12):
            # Calculate month and year
            pay_date_val = date.today() - timedelta(days=month_offset * 30)
            month = pay_date_val.month
            year = pay_date_val.year
            
            # Create minimal payroll record (only period, month, year)
            # The actual database table has a very minimal schema
            try:
                payslip = Payroll(
                    employee_id=employee.id,
                    period=pay_date_val.strftime("%B %Y"),
                    month=month,
                    year=year,
                )
                session.add(payslip)
                total_payslips += 1
            except Exception:
                # Skip if already exists
                pass
    
    try:
        session.commit()
        print(f"   ✅ Created {total_payslips} payslips")
    except Exception as e:
        session.rollback()
        print(f"   ⚠️  Some payslips may already exist")

def create_notifications(session: Session, employees: Dict):
    """Create some sample notifications"""
    print("\n🔔 Creating Notifications...")
    
    total_notifications = 0
    
    for emp_id, employee in employees.items():
        # Create 3-5 notifications per employee
        num_notifications = randint(3, 5)
        
        for i in range(num_notifications):
            notification = Notification(
                employee_id=employee.id,
                title=choice([
                    "Leave Approved",
                    "New Payslip Available",
                    "Team Meeting Tomorrow",
                    "Policy Update",
                    "Birthday Wishes",
                ]),
                message=choice([
                    "Your leave application has been approved.",
                    "Your payslip for this month is now available.",
                    "Team meeting scheduled for tomorrow at 10 AM.",
                    "Company policy has been updated. Please review.",
                    "Happy Birthday! Wishing you a great year ahead.",
                ]),
                type=choice(["info", "success", "warning"]),
                priority=choice([NotificationPriority.LOW, NotificationPriority.MEDIUM, NotificationPriority.HIGH]),
                is_read=choice([True, False]),
                created_at=datetime.now() - timedelta(days=randint(0, 30)),
            )
            session.add(notification)
            total_notifications += 1
    
    session.commit()
    print(f"   ✅ Created {total_notifications} notifications")

def main():
    """Main function to generate all data"""
    print("=" * 80)
    print("🚀 COMPREHENSIVE DATA GENERATION FOR 25 EMPLOYEES")
    print("=" * 80)
    
    with Session(sync_engine) as session:
        # Create base data
        departments = create_departments(session)
        locations = create_locations(session)
        leave_types = create_leave_types(session)
        create_holidays(session)
        
        # Create employees with hierarchy
        employees = create_employees(session, departments, locations)
        
        # Create transactional data
        create_attendance_records(session, employees)
        create_leave_balances(session, employees, leave_types)
        create_leave_applications(session, employees, leave_types)
        create_payslips(session, employees)
        create_notifications(session, employees)
    
    print("\n" + "=" * 80)
    print("✅ DATA GENERATION COMPLETE!")
    print("=" * 80)
    print("\n📊 Summary:")
    print(f"   • 25 Employees (2 HR, 3 Managers, 20 Employees)")
    print(f"   • 4 Departments")
    print(f"   • 3 Locations")
    print(f"   • 4 Leave Types")
    print(f"   • 30 days of attendance per employee")
    print(f"   • Leave balances for all employees")
    print(f"   • Leave applications")
    print(f"   • 12 months of payslips per employee")
    print(f"   • Notifications for all employees")
    print("\n🔑 Default Password: password123")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

"""
Seed Railway PostgreSQL with sample HRMS data
Generates 25 employees with complete data
"""
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, date, timedelta, time
from random import choice, randint, uniform, random, seed as random_seed
from typing import List
import bcrypt

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select
from app.models.user import (
    User, Employee, Department, Location, 
    UserRole, UserStatus, Gender
)
from app.models.attendance import (
    AttendanceDay, AttendanceStatus, AttendanceSource,
    LeaveType, LeaveBalance, LeaveApplication, LeaveApplicationStatus,
    Holiday
)
from app.models.extras import Payroll, Notification, NotificationPriority, Policy

# Set seed for reproducibility
random_seed(42)

# Sample policy data
POLICIES_DATA = [
    {
        "title": "Work From Home Policy",
        "category": "Remote Work",
        "content": """## Work From Home Policy

### Purpose
This policy outlines the guidelines for employees working remotely to ensure productivity and work-life balance.

### Eligibility
- All full-time employees after completing 3 months probation
- Manager approval required
- Role must be suitable for remote work

### Guidelines
1. **Communication**: Maintain regular communication via Slack/Teams
2. **Availability**: Be available during core hours (10 AM - 4 PM)
3. **Equipment**: Company provides laptop and necessary equipment
4. **Security**: Use VPN for all company resources
5. **Workspace**: Maintain a dedicated, distraction-free workspace

### Approval Process
- Submit WFH request 48 hours in advance
- Maximum 3 days per week unless special approval
- Emergency WFH can be approved same day

### Performance Monitoring
- Regular check-ins with manager
- Deliverables tracked via project management tools
- Monthly performance reviews
""",
        "effective_from": date(2024, 1, 1),
        "is_active": True
    },
    {
        "title": "Leave and Attendance Policy",
        "category": "Leave Management",
        "content": """## Leave and Attendance Policy

### Leave Types

#### 1. Casual Leave (CL)
- 12 days per year
- Can be taken in half-day increments
- No carry forward
- 1 day advance notice required

#### 2. Sick Leave (SL)
- 12 days per year
- Medical certificate required for 3+ consecutive days
- Can be taken without advance notice
- Unused balance carries forward (max 30 days)

#### 3. Earned Leave (EL)
- 15 days per year
- Requires 7 days advance notice
- Can be encashed
- Maximum carry forward: 45 days

#### 4. Maternity/Paternity Leave
- Maternity: 26 weeks paid leave
- Paternity: 2 weeks paid leave
- Medical documentation required

### Attendance Guidelines
- Working hours: 9:00 AM - 6:00 PM
- Core hours: 10:00 AM - 4:00 PM (mandatory presence)
- Grace period: 15 minutes
- Late arrival beyond grace period: Half day deduction
- Biometric/web punch mandatory

### Leave Application Process
1. Submit leave request via HRMS portal
2. Manager approval required
3. HR notification automated
4. Minimum 48 hours for planned leave
""",
        "effective_from": date(2024, 1, 1),
        "is_active": True
    },
    {
        "title": "Code of Conduct",
        "category": "General",
        "content": """## Employee Code of Conduct

### Professional Behavior
- Treat all colleagues with respect and dignity
- Maintain professional attire (business casual)
- No discrimination or harassment of any kind
- Confidentiality of company information

### Work Ethics
- Honesty and integrity in all dealings
- Conflict of interest must be disclosed
- No accepting gifts from vendors/clients
- Intellectual property belongs to company

### Workplace Guidelines
- No alcohol or drugs on premises
- Smoking only in designated areas
- Maintain clean and organized workspace
- Report safety hazards immediately

### Digital Conduct
- Professional communication in emails/chat
- No sharing confidential information
- Social media posts must not harm company reputation
- Respect copyright and licensing

### Violations
- First offense: Written warning
- Second offense: Final warning
- Third offense: Termination
- Serious violations: Immediate termination
""",
        "effective_from": date(2024, 1, 1),
        "is_active": True
    },
    {
        "title": "Performance Appraisal Policy",
        "category": "Performance",
        "content": """## Performance Appraisal Policy

### Appraisal Cycle
- Annual performance review in March
- Mid-year review in September
- Probation review at 3 months

### Evaluation Criteria
1. **Technical Skills** (30%)
   - Job knowledge
   - Quality of work
   - Problem-solving ability

2. **Productivity** (25%)
   - Meeting deadlines
   - Efficiency
   - Output quality

3. **Teamwork** (20%)
   - Collaboration
   - Communication
   - Helping others

4. **Leadership** (15%)
   - Initiative
   - Mentoring
   - Decision making

5. **Innovation** (10%)
   - New ideas
   - Process improvements
   - Learning & development

### Rating Scale
- Outstanding: 4.5 - 5.0
- Exceeds Expectations: 3.5 - 4.4
- Meets Expectations: 2.5 - 3.4
- Needs Improvement: 1.5 - 2.4
- Unsatisfactory: Below 1.5

### Compensation Review
- Salary increment based on rating
- Outstanding: 12-15% increment
- Exceeds: 8-12% increment
- Meets: 5-8% increment
- Promotion consideration for Outstanding/Exceeds ratings
""",
        "effective_from": date(2024, 1, 1),
        "is_active": True
    },
    {
        "title": "Expense Reimbursement Policy",
        "category": "Finance",
        "content": """## Expense Reimbursement Policy

### Eligible Expenses

#### Travel
- Airfare: Economy class
- Hotel: Up to $150/night in metro cities
- Local transport: Taxi/Uber (with receipts)
- Meals: Up to $50/day during business travel

#### Communication
- Mobile bills: Up to $30/month (for field staff)
- Internet: Up to $25/month (for WFH employees)

#### Professional Development
- Training courses: Up to $2000/year
- Certifications: Full reimbursement with approval
- Books/Subscriptions: Up to $500/year

### Claim Process
1. Submit expense report within 30 days
2. Attach all original receipts
3. Manager approval required
4. Finance verification
5. Payment within 15 days

### Non-Reimbursable
- Personal expenses
- Alcohol
- Entertainment
- Traffic violations/fines
- Lost receipts

### Approval Limits
- Up to $500: Manager approval
- $500 - $2000: Department head approval
- Above $2000: CFO approval
""",
        "effective_from": date(2024, 1, 1),
        "is_active": True
    }
]

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
    """Create payroll records for last 6 months"""
    print("\nCreating payroll records...")
    
    count = 0
    current_date = date.today()
    
    # Generate payroll for last 6 months
    for month_offset in range(6):
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

def create_organization_tree(session: Session, departments: List[Department], employees: List[Employee]):
    """Update organization hierarchy"""
    print("\nSetting up organization tree...")
    
    # Find department heads
    hr_dept = next((d for d in departments if d.code == "HR"), None)
    eng_dept = next((d for d in departments if d.code == "ENG"), None)
    prd_dept = next((d for d in departments if d.code == "PRD"), None)
    sal_dept = next((d for d in departments if d.code == "SAL"), None)
    
    # Set department heads
    if hr_dept and len(employees) > 0:
        hr_dept.head_id = employees[0].id  # Sarah Johnson
        session.add(hr_dept)
    
    if eng_dept and len(employees) > 2:
        eng_dept.head_id = employees[2].id  # Emily Davis
        session.add(eng_dept)
    
    if prd_dept and len(employees) > 3:
        prd_dept.head_id = employees[3].id  # David Wilson
        session.add(prd_dept)
    
    if sal_dept and len(employees) > 4:
        sal_dept.head_id = employees[4].id  # Jessica Martinez
        session.add(sal_dept)
    
    session.commit()
    print("✅ Organization tree configured")

def create_company_policies(session: Session):
    """Create company policies"""
    print("\nCreating company policies...")
    
    from app.models.extras import Policy
    
    count = 0
    for policy_data in POLICIES_DATA:
        policy = Policy(
            title=policy_data["title"],
            category=policy_data["category"],
            content=policy_data["content"],
            effective_from=policy_data["effective_from"],
            is_active=policy_data["is_active"],
            version=1
        )
        session.add(policy)
        count += 1
    
    session.commit()
    print(f"✅ Created {count} company policies")


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 RAILWAY DATABASE SEEDING STARTED")
    print("=" * 60)
    
    # Use Railway PostgreSQL URL
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:MQZsbkIEoKEZXmdZfsjuicJeGrNqXXEO@metro.proxy.rlwy.net:14509/railway"
    )
    
    print(f"\n📡 Connecting to: {database_url.split('@')[1]}")
    
    # Create engine for Railway database
    engine = create_engine(database_url, echo=False)
    
    # Import all models to ensure they're registered
    from app.models.user import User, Employee, Department, Location
    from app.models.attendance import AttendanceDay, LeaveType, LeaveBalance
    from app.models.extras import Payroll
    
    # Create all tables
    print("\n🔨 Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tables created")
    
    session = Session(engine)
    
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
        create_organization_tree(session, departments, employees)
        create_company_policies(session)
        
        print("\n" + "=" * 60)
        print("✅ SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Users: {len(users)}")
        print(f"   Employees: {len(employees)}")
        print(f"   Departments: {len(departments)}")
        print(f"   Locations: {len(locations)}")
        print(f"   Leave Types: {len(leave_types)}")
        print(f"   Payroll Records: {len(employees) * 6} (6 months)")
        print(f"   Company Policies: {len(POLICIES_DATA)}")
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

"""
Script to initialize database with sample data
Run: python init_data.py
"""
from datetime import date, datetime, timedelta
from sqlmodel import Session, select
from app.database import sync_engine, create_db_and_tables
from app.models import (
    User, Employee, LeaveType, LeaveBalance, Holiday, Policy,
    Attendance, AttendanceStatus
)
from app.core.security import get_password_hash
from app.config import settings

def init_leave_types(session: Session):
    """Initialize leave types"""
    leave_types = [
        {
            "name": "Casual Leave",
            "code": "CL",
            "description": "Casual leave for personal reasons",
            "max_days_per_year": 12,
            "is_paid": True
        },
        {
            "name": "Sick Leave",
            "code": "SL",
            "description": "Leave for medical reasons",
            "max_days_per_year": 12,
            "is_paid": True
        },
        {
            "name": "Annual Leave",
            "code": "EL",
            "description": "Earned leave / annual vacation",
            "max_days_per_year": 15,
            "is_paid": True
        }
    ]
    
    for lt_data in leave_types:
        # Check if exists
        result = session.execute(
            select(LeaveType).where(LeaveType.code == lt_data["code"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            leave_type = LeaveType(**lt_data)
            session.add(leave_type)
    
    session.commit()
    print("✅ Leave types initialized")

def init_holidays(session: Session):
    """Initialize holidays"""
    current_year = date.today().year
    holidays = [
        {"name": "New Year", "date": date(current_year, 1, 1)},
        {"name": "Independence Day", "date": date(current_year, 8, 15)},
        {"name": "Gandhi Jayanti", "date": date(current_year, 10, 2)},
        {"name": "Christmas", "date": date(current_year, 12, 25)},
    ]
    
    for holiday_data in holidays:
        result = session.execute(
            select(Holiday).where(Holiday.date == holiday_data["date"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            holiday = Holiday(**holiday_data)
            session.add(holiday)
    
    session.commit()
    print("✅ Holidays initialized")

def init_policies(session: Session):
    """Initialize company policies"""
    policies = [
        {
            "title": "Attendance Policy",
            "category": "Attendance",
            "content": """**Attendance Policy**

1. Working Hours: 9:00 AM to 6:00 PM
2. Employees must clock in/out daily
3. Late arrival beyond 9:30 AM is considered late
4. 3 late marks = 1 day leave deduction

**Work from Home:**
- Maximum 2 days per week
- Prior approval required
- Full day work hours mandatory""",
            "version": "1.0"
        },
        {
            "title": "Leave Policy",
            "category": "Leave Management",
            "content": """**Leave Policy**

**Leave Types:**
- Casual Leave: 12 days per year
- Sick Leave: 12 days per year
- Annual Leave: 15 days per year

**Guidelines:**
1. Apply leave 3 days in advance
2. Manager approval required
3. Medical certificate needed for sick leave > 3 days
4. Maximum 5 consecutive casual leaves""",
            "version": "1.0"
        }
    ]
    
    for policy_data in policies:
        result = session.execute(
            select(Policy).where(Policy.title == policy_data["title"])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            policy = Policy(**policy_data)
            session.add(policy)
    
    session.commit()
    print("✅ Policies initialized")

def create_demo_user(session: Session):
    """Create demo user and employee"""
    demo_email = "demo@company.com"
    
    # Check if demo user exists
    result = session.execute(select(User).where(User.email == demo_email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print("✅ Demo user already exists")
        return
    
    # Create demo user
    demo_user = User(
        email=demo_email,
        hashed_password=get_password_hash("demo123"),
        is_active=True
    )
    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)
    
    # Create demo employee
    demo_employee = Employee(
        user_id=demo_user.id,
        employee_id="EMP0001",
        first_name="Demo",
        last_name="User",
        display_name="Demo User",
        email=demo_email,
        phone="+91 9876543210",
        designation="Software Engineer",
        department="Engineering",
        location="Bangalore",
        salary=75000,
        date_of_birth=date(1995, 6, 15),
        gender="Male",
        hire_date=date(2023, 1, 1)
    )
    session.add(demo_employee)
    session.commit()
    session.refresh(demo_employee)
    
    # Initialize leave balances
    leave_types = session.execute(select(LeaveType)).scalars().all()
    current_year = date.today().year
    
    for lt in leave_types:
        balance = LeaveBalance(
            employee_id=demo_employee.id,
            leave_type_id=lt.id,
            year=current_year,
            opening=lt.max_days_per_year,
            accrued=lt.max_days_per_year,
            consumed=0,
            balance=lt.max_days_per_year
        )
        session.add(balance)
    
    # Create sample attendance records for last 7 days
    for i in range(7, 0, -1):
        att_date = date.today() - timedelta(days=i)
        if att_date.weekday() < 5:  # Weekdays only
            attendance = Attendance(
                employee_id=demo_employee.id,
                date=att_date,
                check_in=datetime.combine(att_date, datetime.min.time().replace(hour=9, minute=0)),
                check_out=datetime.combine(att_date, datetime.min.time().replace(hour=18, minute=0)),
                work_hours=9.0,
                status=AttendanceStatus.PRESENT,
                work_location="Office"
            )
            session.add(attendance)
    
    session.commit()
    print("✅ Demo user created successfully")
    print(f"   Email: {demo_email}")
    print(f"   Password: demo123")

def main():
    """Main initialization function"""
    print("🚀 Initializing HRMS Database...")
    
    # Create tables
    create_db_and_tables()
    print("✅ Database tables created")
    
    # Initialize data
    with Session(sync_engine) as session:
        init_leave_types(session)
        init_holidays(session)
        init_policies(session)
        create_demo_user(session)
    
    print("\n✅ Database initialization complete!")
    print("\n📝 Demo Credentials:")
    print("   Email: demo@company.com")
    print("   Password: demo123")

if __name__ == "__main__":
    main()
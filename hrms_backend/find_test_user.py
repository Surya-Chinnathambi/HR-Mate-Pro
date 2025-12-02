"""Quick script to find a valid test user"""
from app.database import get_session
from app.models import Employee, User
from sqlalchemy import select

session = next(get_session())

# Find an employee with a user account
emp = session.execute(
    select(Employee).where(Employee.user_id.is_not(None)).limit(1)
).scalar_one_or_none()

if emp:
    user = session.execute(select(User).where(User.id == emp.user_id)).scalar_one_or_none()
    print(f"✅ Found test user:")
    print(f"   Employee: {emp.first_name} {emp.last_name}")
    print(f"   Email: {user.email}")
    print(f"   Password: Check the original setup - likely 'password123' or similar")
    print(f"\nTest credentials:")
    print(f"   username: {user.email}")
    print(f"   password: <original password>")
else:
    print("❌ No employees with user accounts found")

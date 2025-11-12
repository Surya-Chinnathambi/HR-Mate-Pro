from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import Employee

session = Session(sync_engine)

# Assign HR role to employees 9 and 10 (Kope and Teja)
employee_ids = [9, 10]

for emp_id in employee_ids:
    employee = session.get(Employee, emp_id)
    if employee:
        print(f"Updating {employee.first_name} (ID: {emp_id})")
        print(f"  Before: role={employee.role}, team_id={employee.team_id}")
        
        employee.role = "hr"
        employee.team_id = None  # HR has no team restriction
        session.add(employee)
        
        print(f"  After:  role={employee.role}, team_id={employee.team_id}")
    else:
        print(f"Employee ID {emp_id} not found")

session.commit()
print("\n✅ HR roles assigned successfully!")

# Show updated distribution
employees = session.exec(select(Employee).where(Employee.is_active == True)).all()
print(f"\nUpdated Role Distribution:")
print(f"HR: {len([e for e in employees if e.role == 'hr'])} employees")
print(f"Managers: {len([e for e in employees if e.role == 'manager'])} employees")
print(f"Employees: {len([e for e in employees if e.role == 'employee'])} employees")

session.close()

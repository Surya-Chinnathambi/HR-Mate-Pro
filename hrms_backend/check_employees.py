from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import Employee

session = Session(sync_engine)
employees = session.exec(select(Employee).where(Employee.is_active == True).order_by(Employee.id)).all()

print('Current Employee Roles and Teams:')
print('=' * 60)
print(f'{"ID":>3} | {"Name":<20} | {"Role":<10} | {"Team"}')
print('-' * 60)

for e in employees:
    team_str = f"Team {e.team_id}" if e.team_id else "None"
    print(f'{e.id:>3} | {e.first_name:<20} | {e.role:<10} | {team_str}')

print('=' * 60)
print(f'Total Employees: {len(employees)}')
print(f'Managers: {len([e for e in employees if e.role == "manager"])}')
print(f'HR: {len([e for e in employees if e.role == "hr"])}')
print(f'Employees: {len([e for e in employees if e.role == "employee"])}')

session.close()

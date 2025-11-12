"""
Quick setup script for role-based access and chat history

Run this after migration to configure employee roles and teams
"""
import sys
sys.path.append('c:/forlast/hrms_backend')

from app.database import sync_engine, get_session
from sqlmodel import Session, select
from app.models.user import Employee

def setup_roles_and_teams():
    """
    Configure employee roles and team structure:
    - 2 HR (employees 1, 2)
    - 6 Managers (employees 3-8)
    - Remaining are employees (9+)
    """
    session = Session(sync_engine)
    
    try:
        # Get all employees
        employees = session.exec(select(Employee).where(Employee.is_active == True)).all()
        
        print(f"Found {len(employees)} active employees")
        
        # Set HR roles
        hr_ids = [1, 2]
        for emp in employees:
            if emp.id in hr_ids:
                emp.role = 'hr'
                emp.is_manager = False
                emp.team_id = None  # HR has no team
                session.add(emp)
                print(f"✅ Set {emp.first_name} {emp.last_name} (ID: {emp.id}) as HR")
        
        # Set Manager roles and create teams
        manager_ids = [3, 4, 5, 6, 7, 8]
        for idx, manager_id in enumerate(manager_ids, start=1):
            for emp in employees:
                if emp.id == manager_id:
                    emp.role = 'manager'
                    emp.is_manager = True
                    emp.team_id = idx  # Team 1-6
                    session.add(emp)
                    print(f"✅ Set {emp.first_name} {emp.last_name} (ID: {emp.id}) as Manager of Team {idx}")
        
        # Assign employees to teams based on their manager_id
        for emp in employees:
            if emp.id not in hr_ids and emp.id not in manager_ids:
                # This is a regular employee
                emp.role = 'employee'
                
                # Assign to team based on manager
                if emp.manager_id:
                    # Find manager's team
                    manager = session.get(Employee, emp.manager_id)
                    if manager and manager.team_id:
                        emp.team_id = manager.team_id
                        session.add(emp)
                        print(f"✅ Assigned {emp.first_name} {emp.last_name} (ID: {emp.id}) to Team {emp.team_id}")
                    else:
                        # No manager or manager has no team, assign to Team 1 by default
                        emp.team_id = 1
                        session.add(emp)
                        print(f"⚠️  Assigned {emp.first_name} {emp.last_name} (ID: {emp.id}) to Team 1 (default)")
                else:
                    # No manager assigned, put in Team 1
                    emp.team_id = 1
                    session.add(emp)
                    print(f"⚠️  Assigned {emp.first_name} {emp.last_name} (ID: {emp.id}) to Team 1 (no manager)")
        
        # Commit all changes
        session.commit()
        print("\n✅ Successfully configured roles and teams!")
        
        # Print summary
        hr_count = session.exec(select(Employee).where(Employee.role == 'hr')).all()
        manager_count = session.exec(select(Employee).where(Employee.role == 'manager')).all()
        employee_count = session.exec(select(Employee).where(Employee.role == 'employee')).all()
        
        print(f"\n📊 Summary:")
        print(f"   HR: {len(hr_count)}")
        print(f"   Managers: {len(manager_count)}")
        print(f"   Employees: {len(employee_count)}")
        
        # Print team distribution
        for team_num in range(1, 7):
            team_members = session.exec(
                select(Employee).where(Employee.team_id == team_num)
            ).all()
            manager = next((e for e in team_members if e.role == 'manager'), None)
            print(f"\n   Team {team_num}: {len(team_members)} members")
            if manager:
                print(f"      Manager: {manager.first_name} {manager.last_name}")
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Setting up roles and teams...\n")
    setup_roles_and_teams()
    print("\n✅ Setup complete! You can now test role-based access.")

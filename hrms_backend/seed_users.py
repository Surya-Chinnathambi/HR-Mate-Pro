"""
Seed script to populate the database with initial users and employees.
Run this script to create the organizational structure with test users.
"""

import asyncio
import json
import sys
from datetime import datetime, date
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import sync_engine
from app.models.user import User, UserStatus, UserRole, Employee
from app.core.security import get_password_hash


def seed_users():
    """Seed the database with initial users and employees."""
    
    # Load seed data
    with open('user_seed_data.json', 'r') as f:
        data = json.load(f)
    
    with Session(sync_engine) as session:
        # Check existing users by email
        existing_emails = {user.email for user in session.exec(select(User)).all()}
        
        if existing_emails:
            print(f"ℹ️  Found {len(existing_emails)} existing users in database.")
            print("   Will skip users that already exist.")
            print()
        
        print("🌱 Starting database seeding...")
        print()
        
        users_created = []
        users_skipped = []
        
        # Create HR Manager
        hr_data = data['organization_structure']['hr']['user']
        
        if hr_data['email'] in existing_emails:
            print(f"⏭️  Skipping HR Manager: {hr_data['first_name']} {hr_data['last_name']} (already exists)")
            users_skipped.append(hr_data['email'])
        else:
            print(f"👤 Creating HR Manager: {hr_data['first_name']} {hr_data['last_name']}")
            
            hr_user = User(
                email=hr_data['email'],
                hashed_password=get_password_hash(hr_data['password']),
                first_name=hr_data['first_name'],
                last_name=hr_data['last_name'],
                role=UserRole.HR,
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(hr_user)
            session.commit()
            session.refresh(hr_user)
            
            hr_employee = Employee(
                user_id=hr_user.id,
                employee_id=hr_data['employee_id'],
                first_name=hr_data['first_name'],
                last_name=hr_data['last_name'],
                display_name=f"{hr_data['first_name']} {hr_data['last_name']}",
                email=hr_data['email'],
                phone=hr_data['phone'],
                designation=hr_data['designation'],
                employment_type=hr_data['employment_type'],
                date_of_joining=datetime.strptime(hr_data['date_of_joining'], '%Y-%m-%d').date(),
                currency=hr_data['currency'],
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(hr_employee)
            session.commit()
            
            users_created.append({
                'name': f"{hr_data['first_name']} {hr_data['last_name']}",
                'email': hr_data['email'],
                'password': hr_data['password'],
                'role': 'HR Manager',
                'employee_id': hr_data['employee_id']
            })
        
        # Create Manager
        mgr_data = data['organization_structure']['manager']['user']
        
        if mgr_data['email'] in existing_emails:
            print(f"⏭️  Skipping Manager: {mgr_data['first_name']} {mgr_data['last_name']} (already exists)")
            users_skipped.append(mgr_data['email'])
        else:
            print(f"👤 Creating Manager: {mgr_data['first_name']} {mgr_data['last_name']}")
            
            mgr_user = User(
                email=mgr_data['email'],
                hashed_password=get_password_hash(mgr_data['password']),
                first_name=mgr_data['first_name'],
                last_name=mgr_data['last_name'],
                role=UserRole.MANAGER,
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(mgr_user)
            session.commit()
            session.refresh(mgr_user)
            
            mgr_employee = Employee(
                user_id=mgr_user.id,
                employee_id=mgr_data['employee_id'],
                first_name=mgr_data['first_name'],
                last_name=mgr_data['last_name'],
                display_name=f"{mgr_data['first_name']} {mgr_data['last_name']}",
                email=mgr_data['email'],
                phone=mgr_data['phone'],
                designation=mgr_data['designation'],
                employment_type=mgr_data['employment_type'],
                date_of_joining=datetime.strptime(mgr_data['date_of_joining'], '%Y-%m-%d').date(),
                currency=mgr_data['currency'],
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(mgr_employee)
            session.commit()
            
            users_created.append({
                'name': f"{mgr_data['first_name']} {mgr_data['last_name']}",
                'email': mgr_data['email'],
                'password': mgr_data['password'],
                'role': 'Engineering Manager',
                'employee_id': mgr_data['employee_id']
            })
        
        # Create Team Members
        for member_data in data['organization_structure']['team_members']:
            if member_data['email'] in existing_emails:
                print(f"⏭️  Skipping Team Member: {member_data['first_name']} {member_data['last_name']} (already exists)")
                users_skipped.append(member_data['email'])
                continue
                
            print(f"👤 Creating Team Member: {member_data['first_name']} {member_data['last_name']}")
            
            member_user = User(
                email=member_data['email'],
                hashed_password=get_password_hash(member_data['password']),
                first_name=member_data['first_name'],
                last_name=member_data['last_name'],
                role=UserRole.EMPLOYEE,
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(member_user)
            session.commit()
            session.refresh(member_user)
            
            member_employee = Employee(
                user_id=member_user.id,
                employee_id=member_data['employee_id'],
                first_name=member_data['first_name'],
                last_name=member_data['last_name'],
                display_name=f"{member_data['first_name']} {member_data['last_name']}",
                email=member_data['email'],
                phone=member_data['phone'],
                designation=member_data['designation'],
                employment_type=member_data['employment_type'],
                date_of_joining=datetime.strptime(member_data['date_of_joining'], '%Y-%m-%d').date(),
                currency=member_data['currency'],
                is_active=True,
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(member_employee)
            session.commit()
            
            users_created.append({
                'name': f"{member_data['first_name']} {member_data['last_name']}",
                'email': member_data['email'],
                'password': member_data['password'],
                'role': member_data['designation'],
                'employee_id': member_data['employee_id']
            })
        
        print()
        print("✅ Database seeding completed successfully!")
        print()
        print("=" * 80)
        print("📋 USER CREDENTIALS SUMMARY")
        print("=" * 80)
        print()
        
        if users_created:
            print(f"✨ {len(users_created)} NEW USERS CREATED:")
            print()
            for user in users_created:
                print(f"Name:        {user['name']}")
                print(f"Role:        {user['role']}")
                print(f"Employee ID: {user['employee_id']}")
                print(f"Email:       {user['email']}")
                print(f"Password:    {user['password']}")
                print("-" * 80)
        
        if users_skipped:
            print()
            print(f"⏭️  {len(users_skipped)} USERS SKIPPED (already exist):")
            print()
            for email in users_skipped:
                print(f"  • {email}")
        
        print()
        print("🔐 Note: All passwords follow the format: FirstName@2024")
        print("💡 Tip: Users should change their passwords after first login")
        print()


if __name__ == "__main__":
    seed_users()

"""
Add 6 months payroll, organization tree, and company policies to Railway PostgreSQL
Run this AFTER initial seeding to add additional data
"""
import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, date
from sqlalchemy import create_engine
from sqlmodel import Session, select

# Railway PostgreSQL URL
DATABASE_URL = "postgresql://postgres:MQZsbkIEoKEZXmdZfsjuicJeGrNqXXEO@metro.proxy.rlwy.net:14509/railway"

print("=" * 60)
print("🚀 ADDING ADDITIONAL DATA TO RAILWAY")
print("=" * 60)
print(f"\n📡 Connecting to: {DATABASE_URL.split('@')[1]}")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Import models
from app.models.user import Employee, Department
from app.models.extras import Payroll, Policy

session = Session(engine)

try:
    # 1. Add 6 months of payroll (instead of 3)
    print("\n📊 Generating 6 months of payroll...")
    
    employees = session.exec(select(Employee)).all()
    current_date = date.today()
    payroll_count = 0
    
    # Delete existing payroll to avoid duplicates
    session.query(Payroll).delete()
    session.commit()
    
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
            payroll_count += 1
    
    session.commit()
    print(f"✅ Created {payroll_count} payroll records (6 months)")
    
    # 2. Setup organization tree
    print("\n🌳 Setting up organization tree...")
    
    departments = session.exec(select(Department)).all()
    
    # Find department heads
    hr_dept = next((d for d in departments if d.code == "HR"), None)
    eng_dept = next((d for d in departments if d.code == "ENG"), None)
    prd_dept = next((d for d in departments if d.code == "PRD"), None)
    sal_dept = next((d for d in departments if d.code == "SAL"), None)
    
    # Set department heads
    if hr_dept and len(employees) > 0:
        hr_dept.head_id = employees[0].id
        session.add(hr_dept)
    
    if eng_dept and len(employees) > 2:
        eng_dept.head_id = employees[2].id
        session.add(eng_dept)
    
    if prd_dept and len(employees) > 3:
        prd_dept.head_id = employees[3].id
        session.add(prd_dept)
    
    if sal_dept and len(employees) > 4:
        sal_dept.head_id = employees[4].id
        session.add(sal_dept)
    
    session.commit()
    print("✅ Organization tree configured")
    
    # 3. Create company policies
    print("\n📜 Creating company policies...")
    
    policies = [
        {
            "title": "Work From Home Policy",
            "category": "Remote Work",
            "content": """## Work From Home Policy

### Purpose
This policy outlines the guidelines for employees working remotely.

### Eligibility
- Full-time employees after 3 months probation
- Manager approval required
- Role must be suitable for remote work

### Guidelines
1. Communication: Maintain regular communication
2. Availability: Core hours 10 AM - 4 PM
3. Equipment: Company provides necessary tools
4. Security: Use VPN for all company resources

### Approval Process
- Submit request 48 hours in advance
- Maximum 3 days per week
- Emergency WFH same day approval
""",
            "effective_from": date(2024, 1, 1)
        },
        {
            "title": "Leave and Attendance Policy",
            "category": "Leave Management",
            "content": """## Leave and Attendance Policy

### Leave Types
- Casual Leave: 12 days/year
- Sick Leave: 12 days/year
- Earned Leave: 15 days/year
- Maternity: 26 weeks
- Paternity: 2 weeks

### Attendance
- Working hours: 9 AM - 6 PM
- Core hours: 10 AM - 4 PM
- Grace period: 15 minutes
- Biometric/web punch mandatory
""",
            "effective_from": date(2024, 1, 1)
        },
        {
            "title": "Code of Conduct",
            "category": "General",
            "content": """## Employee Code of Conduct

### Professional Behavior
- Respect and dignity for all
- Professional attire
- No discrimination or harassment
- Confidentiality maintained

### Work Ethics
- Honesty and integrity
- Disclose conflicts of interest
- No gifts from vendors
- IP belongs to company
""",
            "effective_from": date(2024, 1, 1)
        },
        {
            "title": "Performance Appraisal Policy",
            "category": "Performance",
            "content": """## Performance Appraisal Policy

### Appraisal Cycle
- Annual review: March
- Mid-year review: September
- Probation review: 3 months

### Rating Scale
- Outstanding: 4.5-5.0 (12-15% increment)
- Exceeds: 3.5-4.4 (8-12% increment)
- Meets: 2.5-3.4 (5-8% increment)
- Needs Improvement: 1.5-2.4
- Unsatisfactory: Below 1.5
""",
            "effective_from": date(2024, 1, 1)
        },
        {
            "title": "Expense Reimbursement Policy",
            "category": "Finance",
            "content": """## Expense Reimbursement Policy

### Eligible Expenses
- Travel: Economy airfare, hotels $150/night
- Communication: Mobile $30/month, Internet $25/month
- Training: Up to $2000/year
- Certifications: Full reimbursement

### Claim Process
1. Submit within 30 days
2. Attach original receipts
3. Manager approval required
4. Payment within 15 days

### Approval Limits
- Up to $500: Manager
- $500-$2000: Department head
- Above $2000: CFO
""",
            "effective_from": date(2024, 1, 1)
        }
    ]
    
    policy_count = 0
    for policy_data in policies:
        policy = Policy(
            title=policy_data["title"],
            category=policy_data["category"],
            content=policy_data["content"],
            effective_from=policy_data["effective_from"],
            is_active=True,
            version=1
        )
        session.add(policy)
        policy_count += 1
    
    session.commit()
    print(f"✅ Created {policy_count} company policies")
    
    print("\n" + "=" * 60)
    print("✅ ADDITIONAL DATA ADDED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   Payroll Records: {payroll_count} (6 months)")
    print(f"   Organization Tree: Configured")
    print(f"   Company Policies: {policy_count}")
    print("=" * 60)

except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    raise
finally:
    session.close()

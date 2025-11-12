"""
Payroll and Salary Models
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import date
import enum

from app.database import Base


class PayrollStatus(str, enum.Enum):
    """Payroll processing status"""
    DRAFT = "draft"
    PROCESSED = "processed"
    PAID = "paid"
    CANCELLED = "cancelled"


class Payroll(Base):
    """Monthly payroll records"""
    __tablename__ = "payrolls"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Pay period
    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=True)
    
    # Earnings
    basic_salary = Column(Float, default=0)
    hra = Column(Float, default=0)  # House Rent Allowance
    special_allowance = Column(Float, default=0)
    transport_allowance = Column(Float, default=0)
    medical_allowance = Column(Float, default=0)
    other_allowances = Column(Float, default=0)
    gross_salary = Column(Float, default=0)
    
    # Deductions
    pf_employee = Column(Float, default=0)  # Employee PF contribution
    pf_employer = Column(Float, default=0)  # Employer PF contribution
    income_tax = Column(Float, default=0)  # TDS
    professional_tax = Column(Float, default=0)
    other_deductions = Column(Float, default=0)
    total_deductions = Column(Float, default=0)
    
    # Net salary
    net_salary = Column(Float, default=0)
    
    # Payment details
    payment_mode = Column(String(50), default="Bank Transfer")
    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT)
    
    # Relationships
    employee = relationship("Employee", back_populates="payrolls")
    
    def __repr__(self):
        return f"<Payroll employee_id={self.employee_id} period={self.pay_period_start.strftime('%Y-%m')}>"

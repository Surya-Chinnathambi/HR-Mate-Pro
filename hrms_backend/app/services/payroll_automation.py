"""
Payroll Automation Service
Provides automated payslip access and salary information
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from decimal import Decimal


class PayrollAutomationService:
    """
    Automated payroll and salary information service
    - Payslip access and viewing
    - Salary breakdown (gross, deductions, net)
    - YTD earnings and tax summary
    - Investment declaration status
    - Salary history and comparisons
    """
    
    # Tax slabs (Indian tax structure - example)
    TAX_SLABS = [
        {"min": 0, "max": 250000, "rate": 0},
        {"min": 250000, "max": 500000, "rate": 5},
        {"min": 500000, "max": 750000, "rate": 10},
        {"min": 750000, "max": 1000000, "rate": 15},
        {"min": 1000000, "max": 1250000, "rate": 20},
        {"min": 1250000, "max": 1500000, "rate": 25},
        {"min": 1500000, "max": float('inf'), "rate": 30}
    ]
    
    @staticmethod
    async def get_latest_payslip(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Get latest payslip with complete breakdown
        Returns salary components, deductions, and net pay
        """
        from app.models import Payroll, Employee
        
        # Get latest payroll record
        stmt = select(Payroll).where(
            Payroll.employee_id == employee_id
        ).order_by(desc(Payroll.pay_period_start)).limit(1)
        
        result = await db.execute(stmt)
        payroll = result.scalar_one_or_none()
        
        if not payroll:
            return {
                "success": False,
                "error": "no_payslip_found",
                "message": "No payslip records found. Please contact HR."
            }
        
        # Get employee details
        stmt_emp = select(Employee).where(Employee.id == employee_id)
        result_emp = await db.execute(stmt_emp)
        employee = result_emp.scalar_one_or_none()
        
        # Parse salary components
        basic_salary = float(payroll.basic_salary or 0)
        hra = float(payroll.hra or 0)
        special_allowance = float(payroll.special_allowance or 0)
        transport_allowance = float(payroll.transport_allowance or 0)
        medical_allowance = float(payroll.medical_allowance or 0)
        other_allowances = float(payroll.other_allowances or 0)
        
        gross_salary = float(payroll.gross_salary or 0)
        
        # Parse deductions
        pf_deduction = float(payroll.pf_employee or 0)
        tax_deduction = float(payroll.income_tax or 0)
        professional_tax = float(payroll.professional_tax or 0)
        other_deductions = float(payroll.other_deductions or 0)
        
        total_deductions = float(payroll.total_deductions or 0)
        net_salary = float(payroll.net_salary or 0)
        
        # Format pay period
        pay_period = f"{payroll.pay_period_start.strftime('%B %Y')}"
        
        return {
            "success": True,
            "payslip": {
                "employee": {
                    "id": employee.id,
                    "name": f"{employee.first_name} {employee.last_name}",
                    "employee_code": employee.employee_code,
                    "designation": employee.designation,
                    "department": employee.department
                },
                "period": pay_period,
                "pay_date": payroll.pay_date.isoformat() if payroll.pay_date else None,
                "earnings": {
                    "basic_salary": basic_salary,
                    "hra": hra,
                    "special_allowance": special_allowance,
                    "transport_allowance": transport_allowance,
                    "medical_allowance": medical_allowance,
                    "other_allowances": other_allowances,
                    "gross_salary": gross_salary
                },
                "deductions": {
                    "provident_fund": pf_deduction,
                    "income_tax": tax_deduction,
                    "professional_tax": professional_tax,
                    "other_deductions": other_deductions,
                    "total_deductions": total_deductions
                },
                "net_pay": net_salary,
                "payment_mode": payroll.payment_mode or "Bank Transfer",
                "payment_status": payroll.status
            },
            "download_info": {
                "available": True,
                "password_protected": True,
                "password_hint": "Your date of birth (DDMMYYYY)",
                "format": "PDF"
            }
        }
    
    @staticmethod
    async def get_salary_breakdown(
        db: AsyncSession,
        employee_id: int,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed salary breakdown with component-wise split
        """
        from app.models import Payroll
        
        # Build query based on month
        if month:
            try:
                target_date = datetime.strptime(month, '%Y-%m')
                stmt = select(Payroll).where(
                    and_(
                        Payroll.employee_id == employee_id,
                        func.extract('year', Payroll.pay_period_start) == target_date.year,
                        func.extract('month', Payroll.pay_period_start) == target_date.month
                    )
                )
            except ValueError:
                return {
                    "success": False,
                    "error": "invalid_month_format",
                    "message": "Invalid month format. Use YYYY-MM"
                }
        else:
            # Latest month
            stmt = select(Payroll).where(
                Payroll.employee_id == employee_id
            ).order_by(desc(Payroll.pay_period_start)).limit(1)
        
        result = await db.execute(stmt)
        payroll = result.scalar_one_or_none()
        
        if not payroll:
            return {
                "success": False,
                "error": "no_payroll_found",
                "message": f"No payroll record found for {month or 'latest month'}"
            }
        
        gross = float(payroll.gross_salary or 0)
        net = float(payroll.net_salary or 0)
        deductions = float(payroll.total_deductions or 0)
        
        # Calculate percentages
        earnings_breakdown = {
            "basic_salary": {
                "amount": float(payroll.basic_salary or 0),
                "percentage": round((float(payroll.basic_salary or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "hra": {
                "amount": float(payroll.hra or 0),
                "percentage": round((float(payroll.hra or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "special_allowance": {
                "amount": float(payroll.special_allowance or 0),
                "percentage": round((float(payroll.special_allowance or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "transport_allowance": {
                "amount": float(payroll.transport_allowance or 0),
                "percentage": round((float(payroll.transport_allowance or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "medical_allowance": {
                "amount": float(payroll.medical_allowance or 0),
                "percentage": round((float(payroll.medical_allowance or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "other_allowances": {
                "amount": float(payroll.other_allowances or 0),
                "percentage": round((float(payroll.other_allowances or 0) / gross * 100) if gross > 0 else 0, 1)
            }
        }
        
        deductions_breakdown = {
            "provident_fund": {
                "amount": float(payroll.pf_employee or 0),
                "percentage": round((float(payroll.pf_employee or 0) / gross * 100) if gross > 0 else 0, 1),
                "employer_contribution": float(payroll.pf_employer or 0)
            },
            "income_tax": {
                "amount": float(payroll.income_tax or 0),
                "percentage": round((float(payroll.income_tax or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "professional_tax": {
                "amount": float(payroll.professional_tax or 0),
                "percentage": round((float(payroll.professional_tax or 0) / gross * 100) if gross > 0 else 0, 1)
            },
            "other_deductions": {
                "amount": float(payroll.other_deductions or 0),
                "percentage": round((float(payroll.other_deductions or 0) / gross * 100) if gross > 0 else 0, 1)
            }
        }
        
        return {
            "success": True,
            "period": f"{payroll.pay_period_start.strftime('%B %Y')}",
            "summary": {
                "gross_salary": gross,
                "total_deductions": deductions,
                "net_salary": net,
                "take_home_percentage": round((net / gross * 100) if gross > 0 else 0, 1)
            },
            "earnings_breakdown": earnings_breakdown,
            "deductions_breakdown": deductions_breakdown,
            "insights": {
                "highest_earning_component": max(
                    earnings_breakdown.items(),
                    key=lambda x: x[1]["amount"]
                )[0].replace("_", " ").title(),
                "highest_deduction_component": max(
                    deductions_breakdown.items(),
                    key=lambda x: x[1]["amount"]
                )[0].replace("_", " ").title(),
                "deduction_rate": round((deductions / gross * 100) if gross > 0 else 0, 1)
            }
        }
    
    @staticmethod
    async def get_ytd_summary(
        db: AsyncSession,
        employee_id: int,
        financial_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get Year-to-Date (YTD) earnings and tax summary
        Financial year: April to March
        """
        from app.models import Payroll
        
        # Determine financial year
        current_date = date.today()
        if not financial_year:
            if current_date.month >= 4:
                financial_year = current_date.year
            else:
                financial_year = current_date.year - 1
        
        # FY start and end dates
        fy_start = date(financial_year, 4, 1)
        fy_end = date(financial_year + 1, 3, 31)
        
        # Get all payroll records for the FY
        stmt = select(Payroll).where(
            and_(
                Payroll.employee_id == employee_id,
                Payroll.pay_period_start >= fy_start,
                Payroll.pay_period_start <= fy_end
            )
        ).order_by(Payroll.pay_period_start)
        
        result = await db.execute(stmt)
        payroll_records = result.scalars().all()
        
        if not payroll_records:
            return {
                "success": False,
                "error": "no_ytd_data",
                "message": f"No payroll data found for FY {financial_year}-{financial_year+1}"
            }
        
        # Calculate YTD totals
        ytd_gross = sum(float(p.gross_salary or 0) for p in payroll_records)
        ytd_net = sum(float(p.net_salary or 0) for p in payroll_records)
        ytd_tax = sum(float(p.income_tax or 0) for p in payroll_records)
        ytd_pf = sum(float(p.pf_employee or 0) for p in payroll_records)
        ytd_deductions = sum(float(p.total_deductions or 0) for p in payroll_records)
        
        months_completed = len(payroll_records)
        months_remaining = 12 - months_completed
        
        # Project annual figures
        if months_completed > 0:
            projected_annual_gross = (ytd_gross / months_completed) * 12
            projected_annual_tax = (ytd_tax / months_completed) * 12
        else:
            projected_annual_gross = 0
            projected_annual_tax = 0
        
        # Determine tax bracket
        tax_bracket = PayrollAutomationService._get_tax_bracket(projected_annual_gross)
        
        return {
            "success": True,
            "financial_year": f"FY {financial_year}-{financial_year+1}",
            "period": {
                "start": fy_start.isoformat(),
                "end": fy_end.isoformat(),
                "months_completed": months_completed,
                "months_remaining": months_remaining
            },
            "ytd_summary": {
                "gross_earnings": round(ytd_gross, 2),
                "net_earnings": round(ytd_net, 2),
                "total_tax_paid": round(ytd_tax, 2),
                "total_pf": round(ytd_pf, 2),
                "total_deductions": round(ytd_deductions, 2)
            },
            "projections": {
                "projected_annual_gross": round(projected_annual_gross, 2),
                "projected_annual_tax": round(projected_annual_tax, 2),
                "projected_annual_net": round(projected_annual_gross - (ytd_deductions / months_completed * 12) if months_completed > 0 else 0, 2)
            },
            "tax_info": {
                "tax_bracket": f"{tax_bracket['rate']}%",
                "bracket_range": f"₹{tax_bracket['min']:,.0f} - ₹{tax_bracket['max']:,.0f}" if tax_bracket['max'] != float('inf') else f"Above ₹{tax_bracket['min']:,.0f}",
                "average_monthly_tax": round(ytd_tax / months_completed, 2) if months_completed > 0 else 0
            },
            "monthly_average": {
                "gross": round(ytd_gross / months_completed, 2) if months_completed > 0 else 0,
                "net": round(ytd_net / months_completed, 2) if months_completed > 0 else 0,
                "deductions": round(ytd_deductions / months_completed, 2) if months_completed > 0 else 0
            }
        }
    
    @staticmethod
    def _get_tax_bracket(annual_income: float) -> Dict[str, Any]:
        """Get tax bracket for given annual income"""
        for slab in PayrollAutomationService.TAX_SLABS:
            if slab["min"] <= annual_income < slab["max"]:
                return slab
        return PayrollAutomationService.TAX_SLABS[-1]
    
    @staticmethod
    async def get_salary_history(
        db: AsyncSession,
        employee_id: int,
        months: int = 6
    ) -> Dict[str, Any]:
        """
        Get salary history for last N months
        Shows trends and comparisons
        """
        from app.models import Payroll
        
        # Get last N months of payroll
        stmt = select(Payroll).where(
            Payroll.employee_id == employee_id
        ).order_by(desc(Payroll.pay_period_start)).limit(months)
        
        result = await db.execute(stmt)
        payroll_records = result.scalars().all()
        
        if not payroll_records:
            return {
                "success": False,
                "error": "no_history",
                "message": "No salary history found"
            }
        
        # Reverse to get chronological order
        payroll_records = list(reversed(payroll_records))
        
        history = []
        for record in payroll_records:
            history.append({
                "month": record.pay_period_start.strftime('%B %Y'),
                "gross": float(record.gross_salary or 0),
                "deductions": float(record.total_deductions or 0),
                "net": float(record.net_salary or 0),
                "status": record.status
            })
        
        # Calculate statistics
        gross_amounts = [h["gross"] for h in history]
        net_amounts = [h["net"] for h in history]
        
        avg_gross = sum(gross_amounts) / len(gross_amounts) if gross_amounts else 0
        avg_net = sum(net_amounts) / len(net_amounts) if net_amounts else 0
        
        # Check for salary changes
        salary_changes = []
        for i in range(1, len(history)):
            if history[i]["gross"] != history[i-1]["gross"]:
                change_amount = history[i]["gross"] - history[i-1]["gross"]
                change_percent = (change_amount / history[i-1]["gross"] * 100) if history[i-1]["gross"] > 0 else 0
                salary_changes.append({
                    "month": history[i]["month"],
                    "change_amount": round(change_amount, 2),
                    "change_percent": round(change_percent, 2),
                    "type": "increment" if change_amount > 0 else "decrement"
                })
        
        return {
            "success": True,
            "period": f"Last {len(history)} months",
            "history": history,
            "statistics": {
                "average_gross": round(avg_gross, 2),
                "average_net": round(avg_net, 2),
                "highest_month": max(history, key=lambda x: x["net"])["month"],
                "lowest_month": min(history, key=lambda x: x["net"])["month"]
            },
            "salary_changes": salary_changes,
            "insights": {
                "stable_salary": len(salary_changes) == 0,
                "total_changes": len(salary_changes),
                "last_change": salary_changes[-1] if salary_changes else None
            }
        }
    
    @staticmethod
    async def get_investment_declaration_status(
        db: AsyncSession,
        employee_id: int
    ) -> Dict[str, Any]:
        """
        Get investment declaration status for tax saving
        """
        # This would typically query an investment_declarations table
        # For now, returning a template structure
        
        current_fy = date.today().year if date.today().month >= 4 else date.today().year - 1
        
        return {
            "success": True,
            "financial_year": f"FY {current_fy}-{current_fy+1}",
            "declaration_status": "pending",  # pending, submitted, approved
            "sections": {
                "80C": {
                    "name": "Section 80C (PPF, ELSS, Life Insurance, etc.)",
                    "max_limit": 150000,
                    "declared": 0,
                    "status": "not_declared"
                },
                "80D": {
                    "name": "Section 80D (Health Insurance)",
                    "max_limit": 25000,
                    "declared": 0,
                    "status": "not_declared"
                },
                "80E": {
                    "name": "Section 80E (Education Loan Interest)",
                    "max_limit": "No limit",
                    "declared": 0,
                    "status": "not_declared"
                },
                "HRA": {
                    "name": "HRA Exemption",
                    "declared": 0,
                    "status": "not_declared"
                }
            },
            "deadline": f"January 31, {current_fy+1}",
            "reminder": "Submit your investment declarations before the deadline to optimize tax savings"
        }

"""
Expense Claims Automation Service
Provides automated expense management with OCR, categorization, and validation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from decimal import Decimal
import re


class ExpenseAutomationService:
    """
    Automated expense claims service
    - OCR receipt scanning (extract amount, date, merchant)
    - Auto-categorize expense type
    - Policy violation detection
    - Mileage calculation
    - Auto-route to approver
    """
    
    # Expense categories with limits (in INR)
    EXPENSE_CATEGORIES = {
        "travel": {"name": "Travel", "limit_per_claim": 50000, "requires_receipt": True},
        "food": {"name": "Food & Meals", "limit_per_claim": 5000, "requires_receipt": True},
        "accommodation": {"name": "Accommodation", "limit_per_claim": 15000, "requires_receipt": True},
        "fuel": {"name": "Fuel", "limit_per_claim": 10000, "requires_receipt": True},
        "office_supplies": {"name": "Office Supplies", "limit_per_claim": 3000, "requires_receipt": False},
        "internet": {"name": "Internet/Mobile", "limit_per_claim": 2000, "requires_receipt": True},
        "client_entertainment": {"name": "Client Entertainment", "limit_per_claim": 10000, "requires_receipt": True},
        "training": {"name": "Training/Conference", "limit_per_claim": 25000, "requires_receipt": True},
        "mileage": {"name": "Mileage Reimbursement", "limit_per_claim": 20000, "requires_receipt": False},
        "other": {"name": "Other", "limit_per_claim": 5000, "requires_receipt": True}
    }
    
    # Mileage rates (per km)
    MILEAGE_RATES = {
        "two_wheeler": 5.0,  # ₹5 per km
        "four_wheeler": 10.0,  # ₹10 per km
        "company_vehicle": 0.0  # No reimbursement
    }
    
    # City distances (major routes in km)
    CITY_DISTANCES = {
        ("mumbai", "pune"): 148,
        ("mumbai", "nashik"): 167,
        ("mumbai", "surat"): 266,
        ("delhi", "jaipur"): 280,
        ("delhi", "agra"): 206,
        ("bangalore", "mysore"): 144,
        ("bangalore", "chennai"): 346,
        ("hyderabad", "vijayawada"): 275,
        ("chennai", "coimbatore"): 507,
        ("kolkata", "durgapur"): 166
    }
    
    @staticmethod
    async def scan_receipt_ocr(
        image_data: bytes,
        file_name: str
    ) -> Dict[str, Any]:
        """
        OCR receipt scanning to extract key information
        In production, this would use Azure Computer Vision or Tesseract
        For now, returns a simulated response
        """
        # TODO: Integrate with Azure Computer Vision API
        # from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        # from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        
        # Simulated OCR extraction
        # In real implementation, this would:
        # 1. Call Azure CV API with image_data
        # 2. Extract text using OCR
        # 3. Parse text for amount, date, merchant using regex
        
        return {
            "success": True,
            "extracted_data": {
                "merchant_name": "Sample Merchant",  # Would be extracted from OCR
                "amount": 0.0,  # Would be extracted from OCR
                "date": None,  # Would be extracted from OCR
                "tax_amount": 0.0,  # Would be calculated from OCR
                "confidence": 0.0  # OCR confidence score
            },
            "raw_text": "",  # Full OCR text
            "message": "OCR extraction completed. Please verify the extracted details.",
            "requires_manual_review": True  # Flag if confidence is low
        }
    
    @staticmethod
    def categorize_expense(
        description: str,
        amount: float,
        merchant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-categorize expense based on description and merchant
        Uses keyword matching and rules
        """
        description_lower = description.lower() if description else ""
        merchant_lower = merchant.lower() if merchant else ""
        
        # Keyword-based categorization
        category_keywords = {
            "travel": ["flight", "airline", "train", "bus", "taxi", "uber", "ola", "cab", "ticket"],
            "food": ["restaurant", "food", "meal", "lunch", "dinner", "breakfast", "cafe", "swiggy", "zomato"],
            "accommodation": ["hotel", "accommodation", "lodge", "stay", "airbnb", "oyo"],
            "fuel": ["petrol", "diesel", "fuel", "gas", "cng"],
            "office_supplies": ["stationery", "office", "supplies", "printer", "paper"],
            "internet": ["internet", "mobile", "recharge", "broadband", "data", "airtel", "jio", "vodafone"],
            "client_entertainment": ["client", "entertainment", "meeting", "conference room"],
            "training": ["training", "course", "seminar", "workshop", "conference", "certification"]
        }
        
        detected_category = "other"
        confidence = 0.0
        
        for category, keywords in category_keywords.items():
            match_count = sum(1 for keyword in keywords if keyword in description_lower or keyword in merchant_lower)
            if match_count > 0:
                category_confidence = min(match_count / len(keywords) * 100, 95)
                if category_confidence > confidence:
                    detected_category = category
                    confidence = category_confidence
        
        category_info = ExpenseAutomationService.EXPENSE_CATEGORIES.get(
            detected_category,
            ExpenseAutomationService.EXPENSE_CATEGORIES["other"]
        )
        
        return {
            "category": detected_category,
            "category_name": category_info["name"],
            "confidence": round(confidence, 1),
            "suggested_alternative": "other" if confidence < 70 else None,
            "auto_categorized": True
        }
    
    @staticmethod
    async def validate_expense_policy(
        db: AsyncSession,
        employee_id: int,
        category: str,
        amount: float,
        expense_date: date,
        has_receipt: bool = False
    ) -> Dict[str, Any]:
        """
        Validate expense against company policies
        """
        from app.models import Employee
        
        violations = []
        warnings = []
        
        # Get category policy
        category_policy = ExpenseAutomationService.EXPENSE_CATEGORIES.get(category)
        if not category_policy:
            violations.append({
                "type": "invalid_category",
                "message": f"Invalid expense category: {category}"
            })
            return {
                "is_valid": False,
                "violations": violations,
                "warnings": warnings
            }
        
        # Check amount limit
        if amount > category_policy["limit_per_claim"]:
            violations.append({
                "type": "amount_exceeds_limit",
                "message": f"Amount ₹{amount:,.2f} exceeds category limit of ₹{category_policy['limit_per_claim']:,.2f}",
                "limit": category_policy["limit_per_claim"],
                "amount": amount
            })
        
        # Check receipt requirement
        if category_policy["requires_receipt"] and not has_receipt:
            violations.append({
                "type": "receipt_required",
                "message": f"Receipt is mandatory for {category_policy['name']} expenses"
            })
        
        # Check expense date (not future, not too old)
        today = date.today()
        if expense_date > today:
            violations.append({
                "type": "future_date",
                "message": "Expense date cannot be in the future"
            })
        
        days_old = (today - expense_date).days
        if days_old > 90:
            violations.append({
                "type": "expense_too_old",
                "message": f"Expense is {days_old} days old. Claims must be submitted within 90 days."
            })
        elif days_old > 60:
            warnings.append({
                "type": "expense_aging",
                "message": f"Expense is {days_old} days old. Submit claims within 60 days for faster processing."
            })
        
        # Check monthly limit for certain categories
        from app.models.workflow import WorkAssignment  # Using as ExpenseClaim placeholder
        # TODO: Query actual expense claims table
        # For now, simulate monthly limit check
        
        # Warning for high-value claims
        if amount > 10000:
            warnings.append({
                "type": "high_value",
                "message": f"High-value claim (₹{amount:,.2f}) will require additional approval"
            })
        
        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "requires_manager_approval": amount > 5000,
            "requires_finance_approval": amount > 15000
        }
    
    @staticmethod
    def calculate_mileage(
        from_city: str,
        to_city: str,
        vehicle_type: str = "four_wheeler",
        custom_distance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate mileage reimbursement
        """
        from_city_normalized = from_city.lower().strip()
        to_city_normalized = to_city.lower().strip()
        
        # Check both directions
        distance = None
        route_key = (from_city_normalized, to_city_normalized)
        reverse_route_key = (to_city_normalized, from_city_normalized)
        
        if route_key in ExpenseAutomationService.CITY_DISTANCES:
            distance = ExpenseAutomationService.CITY_DISTANCES[route_key]
        elif reverse_route_key in ExpenseAutomationService.CITY_DISTANCES:
            distance = ExpenseAutomationService.CITY_DISTANCES[reverse_route_key]
        elif custom_distance:
            distance = custom_distance
        
        if not distance:
            return {
                "success": False,
                "error": "route_not_found",
                "message": f"Route from {from_city} to {to_city} not found. Please provide custom distance.",
                "available_routes": [
                    f"{city1.title()} to {city2.title()}"
                    for city1, city2 in ExpenseAutomationService.CITY_DISTANCES.keys()
                ]
            }
        
        # Get rate
        rate = ExpenseAutomationService.MILEAGE_RATES.get(vehicle_type)
        if not rate:
            return {
                "success": False,
                "error": "invalid_vehicle_type",
                "message": f"Invalid vehicle type: {vehicle_type}",
                "valid_types": list(ExpenseAutomationService.MILEAGE_RATES.keys())
            }
        
        if rate == 0:
            return {
                "success": True,
                "distance_km": distance,
                "rate_per_km": rate,
                "reimbursement_amount": 0.0,
                "message": "Company vehicle - no reimbursement applicable"
            }
        
        reimbursement = distance * rate
        
        return {
            "success": True,
            "route": f"{from_city.title()} to {to_city.title()}",
            "distance_km": distance,
            "vehicle_type": vehicle_type,
            "rate_per_km": rate,
            "reimbursement_amount": round(reimbursement, 2),
            "breakdown": f"{distance} km × ₹{rate}/km = ₹{reimbursement:,.2f}"
        }
    
    @staticmethod
    async def submit_expense_claim(
        db: AsyncSession,
        employee_id: int,
        user_id: int,
        category: str,
        amount: float,
        expense_date: date,
        description: str,
        merchant: Optional[str] = None,
        has_receipt: bool = False,
        receipt_url: Optional[str] = None,
        mileage_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submit expense claim with validation and auto-routing
        Now includes inbox notifications, audit logging, and delivery status
        """
        from app.models import Employee
        from app.models.workflow import ApprovalRequest, RequestType, ApprovalStatus, AuditLog, AuditAction
        from app.services.notification_delivery import NotificationDeliveryService
        from sqlalchemy import text
        import uuid
        
        # Get employee
        stmt = select(Employee).where(Employee.id == employee_id)
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee not found"
            }
        
        # Validate against policy
        validation = await ExpenseAutomationService.validate_expense_policy(
            db=db,
            employee_id=employee_id,
            category=category,
            amount=amount,
            expense_date=expense_date,
            has_receipt=has_receipt
        )
        
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": "policy_violation",
                "message": "Expense claim violates company policy",
                "violations": validation["violations"],
                "warnings": validation["warnings"]
            }
        
        # Determine approver
        approver_id = employee.manager_id
        requires_finance_approval = validation.get("requires_finance_approval", False)
        
        if not approver_id:
            return {
                "success": False,
                "error": "no_manager",
                "message": "No manager assigned. Cannot submit expense claim."
            }
        
        try:
            # Create expense claim data
            expense_claim_data = {
                "employee_id": employee_id,
                "category": category,
                "amount": amount,
                "expense_date": expense_date.isoformat() if isinstance(expense_date, date) else expense_date,
                "description": description,
                "merchant": merchant,
                "has_receipt": has_receipt,
                "receipt_url": receipt_url,
                "mileage_data": mileage_data,
                "submitted_at": datetime.utcnow().isoformat()
            }
            
            # Create approval request
            approval = ApprovalRequest(
                request_type=RequestType.OTHER,  # Would be RequestType.EXPENSE_CLAIM
                requester_id=employee_id,
                approver_id=approver_id,
                status=ApprovalStatus.PENDING,
                request_data=expense_claim_data,
                created_at=datetime.utcnow()
            )
            
            db.add(approval)
            await db.flush()
            
            # Create inbox notifications
            inbox_ids = []
            
            # Notify employee (confirmation)
            employee_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[employee_id],
                notification_type="expense_claim_submitted",
                message_id=None,
                entity_type="expense_claim",
                entity_id=approval.id,
                title=f"Expense Claim Submitted: ₹{amount:,.2f}",
                body=f"Your {category} expense claim for ₹{amount:,.2f} has been submitted for approval. Description: {description}",
                metadata={
                    "category": category,
                    "amount": amount,
                    "expense_date": expense_date.isoformat() if isinstance(expense_date, date) else expense_date,
                    "merchant": merchant,
                    "status": "pending"
                }
            )
            inbox_ids.extend(employee_inbox_ids)
            
            # Notify manager (approval request)
            manager_inbox_ids = await NotificationDeliveryService.create_inbox_notification(
                db=db,
                recipient_employee_ids=[approver_id],
                notification_type="expense_claim_pending",
                message_id=None,
                entity_type="expense_claim",
                entity_id=approval.id,
                title=f"Expense Approval Needed: {employee.first_name} {employee.last_name}",
                body=f"{employee.first_name} {employee.last_name} submitted a {category} expense claim for ₹{amount:,.2f}. Description: {description}",
                metadata={
                    "employee_id": employee_id,
                    "category": category,
                    "amount": amount,
                    "expense_date": expense_date.isoformat() if isinstance(expense_date, date) else expense_date,
                    "requires_action": True
                }
            )
            inbox_ids.extend(manager_inbox_ids)
            
            # Audit log
            audit_log = AuditLog(
                user_id=user_id,
                employee_id=employee_id,
                action=AuditAction.CREATE,
                entity_type="expense_claim",
                entity_id=approval.id,
                description=f"Submitted {category} expense claim for ₹{amount:,.2f}",
                new_value={
                    "category": category,
                    "amount": amount,
                    "expense_date": expense_date.isoformat() if isinstance(expense_date, date) else expense_date,
                    "description": description,
                    "status": "pending"
                },
                success=True
            )
            db.add(audit_log)
            
            await db.commit()
            await db.refresh(approval)
            
            # Build delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=True,
                inbox_created=len(inbox_ids) > 0,
                event_emitted=True,
                audit_logged=True,
                event_channel="expense_claim_events",
                inbox_ids=inbox_ids,
                error=None
            )
            
            return {
                "success": True,
                "claim_id": approval.id,
                "message": "Expense claim submitted successfully",
                "status": "pending_approval",
                "approver": {
                    "id": approver_id,
                    "name": f"{employee.first_name}'s Manager"
                },
                "requires_finance_approval": requires_finance_approval,
                "warnings": validation.get("warnings", []),
                "estimated_processing_days": 3 if not requires_finance_approval else 7,
                "next_steps": [
                    "Your manager will review the claim",
                    "Finance team will verify if amount > ₹15,000" if requires_finance_approval else None,
                    "You'll receive notification once approved"
                ],
                "delivery_status": delivery_status
            }
            
        except Exception as e:
            await db.rollback()
            # Build error delivery status
            delivery_status = NotificationDeliveryService.build_delivery_status(
                entity_created=False,
                inbox_created=False,
                event_emitted=False,
                audit_logged=False,
                event_channel=None,
                inbox_ids=[],
                error=str(e)
            )
            return {
                "success": False,
                "error": "expense_claim_failed",
                "message": f"Failed to submit expense claim: {str(e)}",
                "delivery_status": delivery_status
            }
    
    @staticmethod
    async def get_expense_summary(
        db: AsyncSession,
        employee_id: int,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get expense claims summary for employee
        """
        from app.models.workflow import ApprovalRequest, RequestType
        
        # Default to current month
        if not month or not year:
            today = date.today()
            month = today.month
            year = today.year
        
        # TODO: Query actual expense claims
        # For now, return simulated data
        
        return {
            "success": True,
            "period": f"{datetime(year, month, 1).strftime('%B %Y')}",
            "summary": {
                "total_claimed": 0.0,
                "total_approved": 0.0,
                "total_pending": 0.0,
                "total_rejected": 0.0,
                "claims_count": 0
            },
            "by_category": {},
            "recent_claims": [],
            "message": "No expense claims found for this period"
        }
    
    @staticmethod
    def suggest_split_expense(
        total_amount: float,
        description: str
    ) -> Dict[str, Any]:
        """
        Suggest splitting expense into multiple categories
        Useful for combined expenses (e.g., hotel + meals)
        """
        suggestions = []
        
        # Common split patterns
        if "hotel" in description.lower() or "accommodation" in description.lower():
            # Typically 70% accommodation, 30% food
            suggestions.append({
                "category": "accommodation",
                "amount": round(total_amount * 0.7, 2),
                "description": "Hotel accommodation"
            })
            suggestions.append({
                "category": "food",
                "amount": round(total_amount * 0.3, 2),
                "description": "Meals during stay"
            })
        
        elif "conference" in description.lower() or "training" in description.lower():
            # Typically 60% training, 20% travel, 20% food
            suggestions.append({
                "category": "training",
                "amount": round(total_amount * 0.6, 2),
                "description": "Training/conference fee"
            })
            suggestions.append({
                "category": "travel",
                "amount": round(total_amount * 0.2, 2),
                "description": "Travel to venue"
            })
            suggestions.append({
                "category": "food",
                "amount": round(total_amount * 0.2, 2),
                "description": "Meals during training"
            })
        
        if suggestions:
            return {
                "should_split": True,
                "suggestions": suggestions,
                "message": "This expense might be better split into multiple categories for accurate tracking"
            }
        
        return {
            "should_split": False,
            "message": "No split suggestions for this expense"
        }

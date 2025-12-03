from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
import uuid

from app.database import get_async_session
from app.models import User
from app.models.ai_chat import ConversationHistory
from app.models.attendance import AttendanceDay
from app.core.security import get_current_active_user, check_permission_for_user
from app.config import settings
from app.services.attendance_automation import AttendanceAutomationService
from app.services.wfh_automation import WFHAutomationService
from app.services.leave_automation import LeaveAutomationService
from app.services.balance_automation import BalanceAutomationService
from app.services.payroll_automation import PayrollAutomationService
from app.services.expense_automation import ExpenseAutomationService
from app.services.task_automation import TaskAutomationService
from app.services.additional_automation import (
    PerformanceAutomationService,
    OnboardingAutomationService,
    TrainingAutomationService,
    PolicyAutomationService,
    ITHelpdeskAutomationService
)

router = APIRouter()

# Use Azure OpenAI if available, otherwise try regular OpenAI
if settings.AZURE_OPENAI_KEY:
    client = AsyncOpenAI(
        api_key=settings.AZURE_OPENAI_KEY,
        base_url=settings.AZURE_OPENAI_ENDPOINT
    )
    model_name = settings.AZURE_OPENAI_DEPLOYMENT
elif settings.OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model_name = "gpt-3.5-turbo"
else:
    client = None
    model_name = None

redis_client = None

async def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = await redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
        except:
            return None
    return redis_client

async def save_message_to_redis(session_id: str, user_id: int, conversation_id: uuid.UUID, role: str, content: str, intent: Optional[str] = None, entities: Optional[Dict] = None, db: AsyncSession = None):
    """Save message with context memory to Redis AND PostgreSQL (Layer 2 & 3)"""
    try:
        r = await get_redis()
        
        # Store in today's history (Redis Layer 2)
        if r:
            today_key = f"conv:{session_id}:today"
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "intent": intent,
                "entities": entities or {},
                "conversation_id": str(conversation_id)
            }
            
            await r.lpush(today_key, json.dumps(message))
            await r.ltrim(today_key, 0, 49)  # Keep last 50 messages
            await r.expire(today_key, 86400)  # 24 hours
            
            # Update active conversation context
            context_key = f"ai_context:{session_id}"
            await r.lpush(context_key, json.dumps(message))
            await r.ltrim(context_key, 0, 9)  # Keep last 10 for quick access
            await r.expire(context_key, 86400)
        
        # Save to PostgreSQL for permanent storage (Layer 3)
        if db:
            db_message = ConversationHistory(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                message_type="user_message" if role == "user" else "bot_response",
                message_text=content,
                intent=intent,
                entities=entities or {}
            )
            db.add(db_message)
            await db.commit()
    except Exception as e:
        print(f"Error saving message: {str(e)}")
        pass

async def get_context_from_redis(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve conversation context with entity persistence"""
    try:
        r = await get_redis()
        if not r:
            return []
        
        key = f"ai_context:{session_id}"
        messages = await r.lrange(key, 0, limit - 1)
        parsed = [json.loads(msg) for msg in reversed(messages)]
        
        # Return full context including entities
        return parsed
    except:
        return []

async def extract_entities_from_context(context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract and merge entities from conversation history"""
    entities = {}
    for msg in context:
        if msg.get("entities"):
            entities.update(msg["entities"])
    return entities

async def detect_intent_switch(current_intent: str, context: List[Dict[str, Any]]) -> bool:
    """Detect if user switched intent mid-conversation"""
    if not context or len(context) < 2:
        return False
    
    last_intent = context[-1].get("intent")
    return last_intent and last_intent != current_intent

async def load_old_conversation_from_db(db: AsyncSession, conversation_id: uuid.UUID, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Load old conversation from PostgreSQL (Layer 3)"""
    try:
        stmt = select(ConversationHistory).where(
            ConversationHistory.conversation_id == conversation_id,
            ConversationHistory.user_id == user_id
        ).order_by(ConversationHistory.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        # Convert to dict format (reverse to get chronological order)
        return [{
            "role": msg.role,
            "content": msg.message_text,
            "timestamp": msg.created_at.isoformat(),
            "intent": msg.intent,
            "entities": msg.entities or {}
        } for msg in reversed(messages)]
    except Exception as e:
        print(f"Error loading old conversation: {str(e)}")
        return []

def generate_intent_switch_acknowledgment(old_intent: str, new_intent: str, collected_entities: Dict) -> str:
    """Generate acknowledgment message when user switches intent"""
    intent_phrases = {
        "apply_leave": "apply for leave",
        "clock_in_out": "clock in/out",
        "check_balance": "check your balance",
        "payroll_query": "check your payroll"
    }
    
    old_phrase = intent_phrases.get(old_intent, "that")
    new_phrase = intent_phrases.get(new_intent, "something else")
    
    ack = f"I see you want to {new_phrase} now. "
    
    # Mention pending items from old intent if entities were collected
    if collected_entities and old_intent:
        ack += f"(By the way, we were discussing {old_phrase} earlier - I've saved that context if you want to continue later.) "
    
    return ack

@router.post("/chat")
async def ai_chat(
    prompt: str = Query(..., description="User message"),
    context: Optional[str] = Query(None, description="Additional context"),
    conversation_id: Optional[str] = Query(None, description="Resume specific conversation (UUID)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    AI Chat with 3-Layer Context Memory
    
    Layer 1: Current session (i-1, i)
    Layer 2: Today's history (Redis - 24hrs)  
    Layer 3: Historical context (PostgreSQL - if conversation_id provided)
    
    Features:
    - Entity persistence across turns
    - Intent switch detection and acknowledgment
    - Old conversation resumption
    """
    if not client:
        return {"response": "AI service is not configured. Please contact support.", "error": True}
    
    try:
        session_id = f"user_{current_user.id}"
        
        # Generate or use existing conversation ID
        conv_id = uuid.UUID(conversation_id) if conversation_id else uuid.uuid4()
        is_resuming = conversation_id is not None
        
        # Load conversation context
        conversation_context = []
        
        # Layer 3: Load old conversation if resuming
        if is_resuming:
            old_messages = await load_old_conversation_from_db(session, conv_id, current_user.id, limit=20)
            conversation_context.extend(old_messages)
        
        # Layer 2: Load today's Redis context
        redis_context = await get_context_from_redis(session_id, limit=10)
        
        # Merge contexts (prioritize Redis for recent messages)
        if redis_context:
            conversation_context.extend(redis_context)
        
        # Extract entities from previous messages
        collected_entities = await extract_entities_from_context(conversation_context)
        
        # Detect current intent
        intent = None
        automated_action_result = None  # Store result of automated actions
        
        # Check for comprehensive balance query
        if any(word in prompt.lower() for word in ["my balance", "all balance", "show balance", "check all", "overall balance"]):
            intent = "check_comprehensive_balance"
            
            # 🤖 AUTOMATED ACTION: Get Comprehensive Balance
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await BalanceAutomationService.get_comprehensive_balance(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "comprehensive_balance_check"
        
        elif any(word in prompt.lower() for word in ["leave balance", "check balance", "how many leaves", "leave remaining"]):
            intent = "check_leave_balance"
            
            # 🤖 AUTOMATED ACTION: Check Leave Balance
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await LeaveAutomationService.get_leave_balance(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "leave_balance_check"
        
        elif any(word in prompt.lower() for word in ["apply leave", "apply for leave", "need leave", "take leave", "request leave"]) or (
            any(word in prompt.lower() for word in ["leave", "off"]) and 
            any(word in prompt.lower() for word in ["apply", "need", "take", "want"])
        ):
            intent = "apply_leave"
            
            # 🤖 AUTOMATED ACTION: Leave Application
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                # Check if user is checking eligibility or balance first
                if any(word in prompt.lower() for word in ["can i", "eligible", "allowed", "balance", "how many"]):
                    # Get leave balance
                    automated_action_result = await LeaveAutomationService.get_leave_balance(
                        db=session,
                        employee_id=employee.id
                    )
                    automated_action_result["action_type"] = "leave_balance_for_application"
        
        elif any(word in prompt.lower() for word in ["cancel leave", "cancel my leave", "withdraw leave"]):
            intent = "cancel_leave"
            
            # 🤖 AUTOMATED ACTION: Check for cancellable leaves
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                # Get leave history to show cancellable leaves
                history = await LeaveAutomationService.get_leave_history(
                    db=session,
                    employee_id=employee.id,
                    months=1  # Only recent leaves
                )
                
                # Filter for cancellable leaves (pending/approved, future dates)
                from datetime import date
                cancellable = [
                    leave for leave in history["by_status"]["pending"] + history["by_status"]["approved"]
                    if leave["start_date"] >= date.today().isoformat()
                ]
                
                automated_action_result = {
                    "action_type": "cancellable_leaves",
                    "cancellable_leaves": cancellable,
                    "count": len(cancellable)
                }

        
        elif any(word in prompt.lower() for word in ["wfh", "work from home", "remote work", "work remotely"]):
            intent = "wfh_request"
            
            # 🤖 AUTOMATED ACTION: WFH Request
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                # Check if user wants to check eligibility or WFH summary
                if any(word in prompt.lower() for word in ["can i", "eligible", "allowed", "check"]):
                    # Extract date from prompt (tomorrow, specific date, etc.)
                    from datetime import date
                    wfh_date = None
                    
                    if "tomorrow" in prompt.lower():
                        wfh_date = date.today() + timedelta(days=1)
                    elif "today" in prompt.lower():
                        wfh_date = date.today()
                    # Could add more date parsing here
                    
                    if wfh_date:
                        # Check eligibility
                        eligibility = await WFHAutomationService.check_eligibility(
                            db=session,
                            employee_id=employee.id,
                            wfh_date=wfh_date
                        )
                        
                        coverage = await WFHAutomationService.check_team_coverage(
                            db=session,
                            employee_id=employee.id,
                            wfh_date=wfh_date
                        )
                        
                        automated_action_result = {
                            "action_type": "check_wfh_eligibility",
                            "date": wfh_date.isoformat(),
                            "day_name": wfh_date.strftime('%A'),
                            "eligibility": eligibility,
                            "team_coverage": coverage
                        }
                
                elif any(word in prompt.lower() for word in ["summary", "how many", "used", "remaining"]):
                    # Get WFH summary
                    automated_action_result = await WFHAutomationService.get_wfh_summary(
                        db=session,
                        employee_id=employee.id,
                        weeks=4
                    )
                    automated_action_result["action_type"] = "wfh_summary"
            
        elif any(word in prompt.lower() for word in ["regularize", "regularization", "forgot", "missed punch", "missed clock"]):
            intent = "attendance_regularization"
            
            # 🤖 AUTOMATED ACTION: Attendance Regularization
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                # Check if user wants to see missed punches or submit regularization
                if any(word in prompt.lower() for word in ["show", "check", "list", "what", "any", "do i have"]):
                    # Show missed punches
                    automated_action_result = await AttendanceAutomationService.auto_suggest_regularization(
                        db=session,
                        employee_id=employee.id
                    )
                    automated_action_result["action_type"] = "list_missed_punches"
                    
                elif any(word in prompt.lower() for word in ["yesterday", "forgot to clock out"]) or "forgot" in prompt.lower():
                    # Auto-detect yesterday's issue and suggest regularization
                    from datetime import date
                    yesterday = date.today() - timedelta(days=1)
                    
                    # Check yesterday's attendance
                    stmt_att = select(AttendanceDay).where(
                        AttendanceDay.employee_id == employee.id,
                        AttendanceDay.date == yesterday
                    )
                    result_att = await session.execute(stmt_att)
                    yesterday_att = result_att.scalar_one_or_none()
                    
                    if yesterday_att:
                        issue_found = False
                        suggested_times = {}
                        
                        if not yesterday_att.check_in:
                            issue_found = True
                            suggested_times["check_in"] = "09:30 AM"
                        
                        if not yesterday_att.check_out and yesterday_att.check_in:
                            issue_found = True
                            suggested_times["check_out"] = "06:30 PM"
                        
                        if issue_found:
                            automated_action_result = {
                                "action_type": "suggest_regularization",
                                "date": yesterday.isoformat(),
                                "day_name": yesterday.strftime('%A'),
                                "issues_found": suggested_times,
                                "current_check_in": yesterday_att.check_in.strftime('%I:%M %p') if yesterday_att.check_in else None,
                                "current_check_out": yesterday_att.check_out.strftime('%I:%M %p') if yesterday_att.check_out else None,
                                "suggested_check_in": suggested_times.get("check_in"),
                                "suggested_check_out": suggested_times.get("check_out"),
                                "message": f"I found missing punch(es) for yesterday ({yesterday.strftime('%B %d, %A')})"
                            }
                        else:
                            automated_action_result = {
                                "action_type": "no_issue_found",
                                "message": f"Your attendance for yesterday ({yesterday.strftime('%B %d, %A')}) looks complete."
                            }
                    else:
                        automated_action_result = {
                            "action_type": "no_record_found",
                            "message": f"No attendance record found for yesterday ({yesterday.strftime('%B %d, %A')})"
                        }
                
                # Check if user is providing regularization details (has date/time in message)
                # We'll let the AI handle the conversation flow and collect the details
            
        elif any(word in prompt.lower() for word in ["clock", "attendance", "check in", "check-in", "checkin", "clock in", "punch in"]):
            intent = "clock_in_out"
            
            # 🤖 AUTOMATED ACTION: Clock In/Out
            # Detect if user wants to clock in or out
            if any(word in prompt.lower() for word in ["clock in", "check in", "punch in", "checkin", "clock me in"]):
                # Get employee from user
                from app.models import Employee
                stmt = select(Employee).where(Employee.user_id == current_user.id)
                result = await session.execute(stmt)
                employee = result.scalar_one_or_none()

                if employee:
                        # RBAC: ensure user can clock in for themselves
                        await check_permission_for_user(
                            resource="attendance",
                            action="clock_in",
                            current_user=current_user,
                            session=session,
                            target_employee_id=employee.id
                        )
                        # Execute automated clock in
                        automated_action_result = await AttendanceAutomationService.clock_in(
                            db=session,
                            employee_id=employee.id,
                            user_id=current_user.id,
                            user_lat=None,  # TODO: Get from frontend if available
                            user_lng=None,
                            device_info="AI Chatbot",
                            office_location="mumbai"
                        )
                    
            elif any(word in prompt.lower() for word in ["clock out", "check out", "punch out", "checkout", "clock me out"]):
                # Get employee from user
                from app.models import Employee
                stmt = select(Employee).where(Employee.user_id == current_user.id)
                result = await session.execute(stmt)
                employee = result.scalar_one_or_none()
                
                if employee:
                    # RBAC: ensure user can clock out for themselves
                    await check_permission_for_user(
                        resource="attendance",
                        action="clock_out",
                        current_user=current_user,
                        session=session,
                        target_employee_id=employee.id
                    )
                    # Execute automated clock out
                    automated_action_result = await AttendanceAutomationService.clock_out(
                        db=session,
                        employee_id=employee.id,
                        user_id=current_user.id,
                        user_lat=None,
                        user_lng=None
                    )
        
        elif any(word in prompt.lower() for word in ["payslip", "salary slip", "pay slip", "show payslip", "view payslip", "my payslip"]):
            intent = "view_payslip"
            
            # 🤖 AUTOMATED ACTION: Get Latest Payslip
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await PayrollAutomationService.get_latest_payslip(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "view_payslip"
        
        elif any(word in prompt.lower() for word in ["salary breakdown", "salary details", "salary components", "how much do i earn"]):
            intent = "salary_breakdown"
            
            # 🤖 AUTOMATED ACTION: Get Salary Breakdown
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await PayrollAutomationService.get_salary_breakdown(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "salary_breakdown"
        
        elif any(word in prompt.lower() for word in ["ytd", "year to date", "annual earnings", "yearly earnings", "how much tax", "tax paid"]):
            intent = "ytd_summary"
            
            # 🤖 AUTOMATED ACTION: Get YTD Summary
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await PayrollAutomationService.get_ytd_summary(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "ytd_summary"
        
        elif any(word in prompt.lower() for word in ["salary history", "past salaries", "previous payslips"]):
            intent = "salary_history"
            
            # 🤖 AUTOMATED ACTION: Get Salary History
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await PayrollAutomationService.get_salary_history(
                    db=session,
                    employee_id=employee.id,
                    months=6
                )
                automated_action_result["action_type"] = "salary_history"
        
        elif any(word in prompt.lower() for word in ["claim mileage", "mileage reimbursement", "travel from", "distance from"]):
            intent = "mileage_calculation"
            
            # Extract cities from prompt
            # Simple pattern matching for "from X to Y"
            import re
            match = re.search(r'from\s+(\w+)\s+to\s+(\w+)', prompt.lower())
            
            if match:
                from_city = match.group(1)
                to_city = match.group(2)
                
                # 🤖 AUTOMATED ACTION: Calculate Mileage
                mileage_result = ExpenseAutomationService.calculate_mileage(
                    from_city=from_city,
                    to_city=to_city,
                    vehicle_type="four_wheeler"  # Default, can be asked later
                )
                automated_action_result = mileage_result
                automated_action_result["action_type"] = "mileage_calculation"
        
        elif any(word in prompt.lower() for word in ["submit expense", "claim expense", "expense claim", "reimburse", "reimbursement"]):
            intent = "submit_expense"
            # Conversational flow - collect: category, amount, date, description
            # Will be handled by AI with follow-up questions
        
        elif any(word in prompt.lower() for word in ["expense summary", "my expenses", "expense history"]):
            intent = "expense_summary"
            
            # 🤖 AUTOMATED ACTION: Get Expense Summary
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await ExpenseAutomationService.get_expense_summary(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "expense_summary"
        
        # Feature 5: Task Management
        elif any(word in prompt.lower() for word in ["my tasks", "show tasks", "task list", "what tasks"]):
            intent = "view_tasks"
            
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await TaskAutomationService.get_my_tasks(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "view_tasks"
        
        elif any(word in prompt.lower() for word in ["update task", "mark task", "task status", "complete task"]):
            intent = "update_task"
        
        elif any(word in prompt.lower() for word in ["log time", "time log", "hours worked"]):
            intent = "log_time"
        
        # Feature 6: Performance & Goals
        elif any(word in prompt.lower() for word in ["my goals", "show goals", "goal progress", "objectives"]):
            intent = "view_goals"
            
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await PerformanceAutomationService.get_my_goals(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "view_goals"
        
        # Feature 7: Onboarding
        elif any(word in prompt.lower() for word in ["onboarding", "checklist", "setup tasks"]):
            intent = "onboarding"
            
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await OnboardingAutomationService.get_onboarding_checklist(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "onboarding"
        
        # Feature 8: Training
        elif any(word in prompt.lower() for word in ["training", "courses", "learning", "enroll"]):
            intent = "training"
            
            from app.models import Employee
            stmt = select(Employee).where(Employee.user_id == current_user.id)
            result = await session.execute(stmt)
            employee = result.scalar_one_or_none()
            
            if employee:
                automated_action_result = await TrainingAutomationService.get_available_courses(
                    db=session,
                    employee_id=employee.id
                )
                automated_action_result["action_type"] = "training"
        
        # Feature 9: Policy Search
        elif any(word in prompt.lower() for word in ["policy", "guideline", "procedure", "handbook"]):
            intent = "policy_search"
            
            # Extract search query
            search_query = prompt.lower().replace("policy", "").replace("guideline", "").strip()
            
            automated_action_result = await PolicyAutomationService.search_policy(
                db=session,
                query=search_query if search_query else "general"
            )
            automated_action_result["action_type"] = "policy_search"
        
        # Feature 10: IT Helpdesk
        elif any(word in prompt.lower() for word in ["it issue", "it support", "technical issue", "laptop problem", "password reset"]):
            intent = "it_helpdesk"
            
            # Check for automated solution
            automated_action_result = ITHelpdeskAutomationService.suggest_solution(prompt)
            automated_action_result["action_type"] = "it_helpdesk"
                    
        elif any(word in prompt.lower() for word in ["balance", "remaining"]):
            intent = "check_balance"
        elif any(word in prompt.lower() for word in ["payroll", "salary"]):
            intent = "payroll_query"
        
        # Detect intent switch
        intent_switched = await detect_intent_switch(intent, conversation_context) if intent else False
        intent_switch_ack = ""
        
        if intent_switched and intent:
            old_intent = conversation_context[-1].get("intent")
            intent_switch_ack = generate_intent_switch_acknowledgment(old_intent, intent, collected_entities)
        
        # Build system prompt with context awareness
        resumption_note = ""
        if is_resuming and len(old_messages) > 0:
            last_date = old_messages[-1].get("timestamp", "")
            if last_date:
                try:
                    dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
                    resumption_note = f"\n\n**IMPORTANT**: This is a RESUMED conversation from {dt.strftime('%B %d, %Y at %I:%M %p')}. Acknowledge this by saying 'Continuing from our chat on {dt.strftime('%B %d')}...'"
                except:
                    resumption_note = "\n\n**IMPORTANT**: This is a RESUMED conversation. Acknowledge this."
        
        # Use configured timezone for accurate time display
        import pytz
        from app.config import settings
        
        try:
            local_tz = pytz.timezone(settings.TIMEZONE)
        except:
            # Fallback to IST if timezone not found
            local_tz = pytz.timezone('Asia/Kolkata')
        
        current_datetime = datetime.now(local_tz)
        current_date = current_datetime.strftime('%B %d, %Y')
        current_time = current_datetime.strftime('%I:%M %p')
        user_full_name = current_user.full_name if hasattr(current_user, 'full_name') else 'there'
        
        system_prompt = """You are Kope, an intelligent AI HR Assistant powered by Azure GPT-4.
        
Current User: {}
Employee Name: {}
Date: {}
Current Time: {}
Conversation ID: {}

CONTEXT MEMORY RULES:
1. ALWAYS remember information from previous messages in this conversation
2. If user provided partial information earlier (like "sick" for leave type), use it
3. Never ask for information already collected in this conversation
4. If user switches intent mid-conversation, acknowledge the switch
5. Maintain collected entities across multiple turns
6. Be conversational, helpful, and context-aware

COLLECTED ENTITIES SO FAR:
{json.dumps(collected_entities, indent=2) if collected_entities else "None yet"}

{resumption_note}

{'**AUTOMATED ACTION EXECUTED:**\n' + json.dumps(automated_action_result, indent=2) + '\n\nPresent this information to the user in a friendly, conversational way. Include all validation results, notifications, and smart insights from the action result.\n' if automated_action_result else ''}

CAPABILITIES WITH AUTOMATION:
1. **Clock In/Out** (AUTOMATED - Instant execution!)
   - Just say "clock me in" or "clock me out"
   
2. **Attendance Regularization** (AUTOMATED - Conversational flow!)
   - Detect missed punches automatically
   - Collect required info: date, check-in/out times, reason
   - When user says "I forgot to clock out yesterday" - detect the issue and suggest times
   - When you have ALL info (date, time(s), reason), tell user you'll submit it
   
3. **WFH (Work From Home) Requests** (AUTOMATED - Smart validation!)
   - Check eligibility: post-probation, max 2 days/week
   - Validate team coverage: max 50% team can be WFH same day
   - Check blackout dates automatically
   - When user asks "Can I WFH tomorrow?" - run eligibility check
   - Collect: date, reason
   - Show warnings if team coverage is low
   - When you have date + reason, tell user you'll submit it
   
4. **Leave Management** (AUTOMATED - Conversational flow!)
   - Check balance: "what's my leave balance?" → Show all types with expiring alerts
   - Apply leave: "I need leave next week" → Collect type, dates, reason
   - Cancel leave: "cancel my leave" → Show cancellable leaves list
   - Leave types: Casual (12 days), Sick (10 days), Earned (24 days), Unpaid
   - When applying: Check balance first, validate dates, then ask for reason
   - When you have ALL info (leave_type, start_date, end_date, reason), tell user you'll submit it
   - Handle warnings (low balance, sandwich leave, etc.)
   
5. **Balance Checking** (AUTOMATED - Comprehensive view!)
   - Quick balance: "check my balance" → Leave + Attendance + WFH quota
   - Comprehensive: "show all balances" → Complete HR balance overview
   - Auto-alerts: Low balance, expiring leaves, poor attendance, etc.
   
6. **Payslip & Salary Info** (AUTOMATED - Instant access!)
   - View payslip: "show my payslip" → Latest payslip with full breakdown
   - Salary breakdown: "salary breakdown" → Component-wise details with percentages
   - YTD summary: "how much tax did I pay?" → Year-to-date earnings and tax
   - Salary history: "salary history" → Last 6 months comparison
   - All salary/tax queries are automated - just ask!
   
7. **Expense Claims** (AUTOMATED - Smart processing!)
   - Mileage calculation: "claim mileage from Mumbai to Pune" → Auto-calculate
   - Submit expense: "submit expense" → Collect category, amount, date, description
   - Auto-categorize based on description (travel, food, accommodation, etc.)
   - Policy validation: Check limits, receipt requirements, date constraints
   - Expense summary: "show my expenses" → Monthly summary by category
   - High-value claims (>₹15K) require finance approval
   
8. **Task Management** (AUTOMATED!)
   - View tasks: "show my tasks" → Categorized by status and priority
   - Update status: "mark task as done" → Update task completion
   - Log time: "log 2 hours on task" → Time tracking
   - Managers can assign tasks and check team workload
   
9. **Performance & Goals** (Available!)
   - View goals: "show my goals" → Current objectives and progress
   - Update progress: Track goal completion
   
10. **Onboarding** (Available!)
   - View checklist: "show onboarding" → Setup tasks and progress
   - Track completion of onboarding activities
   
11. **Training & Development** (Available!)
   - View courses: "show training" → Available courses
   - Enroll: Mandatory and optional training
   
12. **Policy & Compliance** (AUTOMATED - Smart search!)
   - Search policies: "leave policy" → Find relevant policies
   - Get policy details instantly
   
13. **IT Helpdesk** (AUTOMATED - Auto-resolution!)
   - IT issues: "password reset" → Automated solution suggestions
   - Create tickets: If no automated fix available
   - Request assets: Laptop, monitor, etc.

8. **HR Policies** (Available)

REGULARIZATION WORKFLOW:
- If user mentions "forgot", "missed", "regularize", "yesterday" → Check for issues

LEAVE WORKFLOW:
- If balance check: Show all leave types with available days and expiring alerts
- If applying: 
  1. Check balance first (already done via automated action if detected)
  2. Ask for leave type if not provided (casual/sick/earned/unpaid)
  3. Ask for dates (start and end)
  4. Ask for reason
  5. When you have all 4 fields, tell user you'll submit it
- If cancelling: Show list of cancellable leaves (future leaves that are pending/approved)

BALANCE CHECK WORKFLOW:
- If user asks "my balance" or "check balance" → Show comprehensive balance
- Include: Leave balance, attendance rate, WFH quota, overtime, pending items
- Highlight any alerts or warnings
- Make it conversational and friendly

PAYSLIP WORKFLOW:
- If user asks "show payslip" or "salary slip" → Display latest payslip details
- Present earnings (basic, HRA, allowances) and deductions (PF, tax, PT) clearly
- If user asks "salary breakdown" → Show component-wise split with percentages
- If user asks about tax/YTD → Show financial year summary and projections
- If user asks "salary history" → Show last 6 months with trends
- Be clear about take-home percentage and tax bracket
- Note: Password protection for PDF downloads (DOB-based)

EXPENSE CLAIM WORKFLOW:
- If user asks "claim mileage from X to Y" → Auto-calculate distance and amount
- Show: distance, rate per km, total reimbursement
- If route not found, ask for custom distance
- If user says "submit expense" → Collect details conversationally:
  1. Category (travel/food/accommodation/fuel/etc.) - auto-suggest based on description
  2. Amount
  3. Date (when expense was incurred)
  4. Description/merchant name
  5. Ask if they have receipt (mandatory for most categories)
- Auto-validate against policy (amount limits, receipt requirements)
- Show warnings for policy violations BEFORE submission
- Inform about approver and processing time
- For high amounts (>₹15K), mention finance approval needed

WFH WORKFLOW:
- If user asks "Can I WFH [date]?" → Run eligibility + coverage checks
- Show: eligibility status, team coverage %, warnings
- If eligible, ask for reason
- Confirm details and inform about manager approval
- If not eligible, explain blocking issues (probation, quota exceeded, etc.)

TASK MANAGEMENT WORKFLOW:
- If user asks "my tasks" or "show tasks" → Display categorized list
- Categories: Overdue (urgent!), Due Soon (next 3 days), In Progress, Pending
- If user wants to update: Ask for task ID and new status (TODO/IN_PROGRESS/DONE/BLOCKED)
- If user wants to log time: Ask for task ID and hours worked
- Show progress: hours logged vs estimated
- For managers: Can assign tasks and view team workload

IT HELPDESK WORKFLOW:
- If user mentions IT issue → First try automated solution
- Common auto-fixes: password reset, laptop issues, software install, VPN, email
- If automated solution available → Show step-by-step fix
- If no automated solution OR user still needs help → Create IT ticket
- Show ticket ID and SLA (24/48 hours based on priority)
- For asset requests: Guide through approval workflow

POLICY SEARCH WORKFLOW:
- If user asks about policy → Search by keywords
- Show: policy title, summary, category, last updated date
- Common searches: leave policy, expense policy, WFH policy, handbook
- If user wants details → Provide full policy content

ONBOARDING WORKFLOW:
- If new employee asks "onboarding" → Show 5-item checklist
- Display progress percentage and pending items
- Items: IT setup, documents, training, team intro, policies
- Guide through completing each item

TRAINING WORKFLOW:
- If user asks "training" or "courses" → Show available and mandatory courses
- Display: course title, duration, provider, status, deadline
- For enrollment: Provide next steps and confirm interest

Be concise, friendly, and use emojis appropriately. Always provide clear next steps."""

        # Escape curly braces in the system prompt to prevent format errors
        system_prompt = system_prompt.replace('{', '{{').replace('}', '}}')
        
        # Format the system prompt with user-specific variables
        system_prompt = system_prompt.format(
            current_user.email,
            user_full_name,
            current_date,
            current_time,
            conv_id
        )

        if context:
            system_prompt += f"\n\nADDITIONAL CONTEXT: {context}"
        
        # Build message history for AI (last 8 messages for context window)
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation_context[-8:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        # Call Azure OpenAI (GPT-5 requires temperature=1)
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=800,
            temperature=1
        )
        
        ai_response = response.choices[0].message.content
        
        # Prepend intent switch acknowledgment if detected
        if intent_switch_ack:
            ai_response = intent_switch_ack + ai_response
        
        # Save messages to Redis AND PostgreSQL
        await save_message_to_redis(session_id, current_user.id, conv_id, "user", prompt, intent=intent, db=session)
        await save_message_to_redis(session_id, current_user.id, conv_id, "assistant", ai_response, intent=intent, db=session)
        
        return {
            "response": ai_response,
            "intent": intent,
            "intent_switched": intent_switched,
            "collected_entities": collected_entities,
            "conversation_id": str(conv_id),
            "is_resumed": is_resuming,
            "conversation_context_size": len(conversation_context),
            "automated_action": automated_action_result  # Include automated action result
        }
        
    except Exception as e:
        print(f"AI Chat Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "response": "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            "error": True,
            "error_details": str(e)
        }

@router.get("/history")
async def get_chat_history(
    limit: int = Query(50, description="Number of messages to retrieve"),
    current_user: User = Depends(get_current_active_user)
):
    """Get today's conversation history from Redis"""
    try:
        session_id = f"user_{current_user.id}"
        r = await get_redis()
        
        if not r:
            return {"messages": [], "total": 0, "error": "Redis not available"}
        
        # Get today's history
        today_key = f"conv:{session_id}:today"
        messages = await r.lrange(today_key, 0, limit - 1)
        
        if not messages:
            return {"messages": [], "total": 0}
        
        parsed = [json.loads(msg) for msg in reversed(messages)]
        
        return {
            "messages": parsed,
            "total": len(parsed),
            "session_date": current_datetime.strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        print(f"History retrieval error: {str(e)}")
        return {"messages": [], "total": 0, "error": str(e)}

@router.delete("/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_active_user)
):
    """Clear today's conversation history"""
    try:
        session_id = f"user_{current_user.id}"
        r = await get_redis()
        
        if r:
            await r.delete(f"ai_context:{session_id}")
            await r.delete(f"conv:{session_id}:today")
        
        return {
            "message": "Conversation history cleared successfully",
            "cleared_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": "Failed to clear history", "details": str(e)}

@router.get("/context-summary")
async def get_context_summary(
    current_user: User = Depends(get_current_active_user)
):
    """Get summary of current conversation context"""
    try:
        session_id = f"user_{current_user.id}"
        r = await get_redis()
        
        if not r:
            return {"total_messages": 0, "has_context": False}
        
        count = await r.llen(f"ai_context:{session_id}")
        context = await get_context_from_redis(session_id, limit=10)
        entities = await extract_entities_from_context(context)
        
        # Get last intent
        last_intent = None
        if context:
            last_intent = context[-1].get("intent")
        
        return {
            "total_messages": count,
            "has_context": count > 0,
            "collected_entities": entities,
            "last_intent": last_intent,
            "context_messages": len(context)
        }
        
    except:
        return {"total_messages": 0, "has_context": False}

@router.get("/conversations")
async def list_past_conversations(
    limit: int = Query(20, description="Number of conversations to retrieve"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's past conversations from PostgreSQL"""
    try:
        # Get distinct conversation IDs with last message timestamp
        stmt = select(
            ConversationHistory.conversation_id,
            ConversationHistory.created_at
        ).where(
            ConversationHistory.user_id == current_user.id
        ).order_by(
            ConversationHistory.created_at.desc()
        ).limit(limit * 10)  # Get more to ensure we get distinct conversations
        
        result = await session.execute(stmt)
        all_messages = result.all()
        
        # Group by conversation_id and get latest message
        conversations = {}
        for conv_id, created_at in all_messages:
            if conv_id not in conversations:
                conversations[conv_id] = {
                    "conversation_id": str(conv_id),
                    "last_message_at": created_at.isoformat(),
                    "date": created_at.strftime('%B %d, %Y'),
                    "time": created_at.strftime('%I:%M %p')
                }
        
        # Convert to list and sort by date
        conv_list = sorted(
            conversations.values(),
            key=lambda x: x["last_message_at"],
            reverse=True
        )[:limit]
        
        return {
            "conversations": conv_list,
            "total": len(conv_list)
        }
        
    except Exception as e:
        print(f"Error listing conversations: {str(e)}")
        return {"conversations": [], "total": 0, "error": str(e)}

@router.get("/conversation/{conversation_id}")
async def get_conversation_details(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get full details of a specific conversation"""
    try:
        conv_id = uuid.UUID(conversation_id)
        messages = await load_old_conversation_from_db(session, conv_id, current_user.id, limit=100)
        
        if not messages:
            return {"error": "Conversation not found", "messages": []}
        
        # Extract summary info
        intents = [msg.get("intent") for msg in messages if msg.get("intent")]
        entities = await extract_entities_from_context(messages)
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "total_messages": len(messages),
            "intents_discussed": list(set(intents)),
            "collected_entities": entities,
            "first_message_at": messages[0].get("timestamp") if messages else None,
            "last_message_at": messages[-1].get("timestamp") if messages else None
        }
        
    except ValueError:
        return {"error": "Invalid conversation ID format", "messages": []}
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        return {"error": str(e), "messages": []}

@router.post("/submit-leave")
async def submit_leave_application(
    leave_type: str = Query(..., description="Leave type (casual, sick, earned, unpaid)"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    reason: str = Query(..., description="Reason for leave"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Submit leave application
    AI chatbot calls this endpoint after collecting all required information
    """
    try:
        from app.models import Employee
        from datetime import datetime
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Parse dates
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except:
            return {
                "success": False,
                "error": "invalid_date_format",
                "message": f"Invalid date format. Use YYYY-MM-DD"
            }
        
        # RBAC: ensure user can submit leave application for themselves
        await check_permission_for_user(
            resource="leave_application",
            action="create",
            current_user=current_user,
            session=session,
            target_employee_id=employee.id
        )

        # Submit leave application
        result = await LeaveAutomationService.submit_leave_application(
            db=session,
            employee_id=employee.id,
            user_id=current_user.id,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason=reason,
            manager_id=employee.manager_id
        )
        
        return result
        
    except Exception as e:
        print(f"Leave submission error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to submit leave application: {str(e)}"
        }

@router.post("/cancel-leave")
async def cancel_leave_request(
    application_id: Optional[int] = Query(None, description="Leave application ID"),
    leave_date: Optional[str] = Query(None, description="Leave date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Cancel leave application
    Can specify by application ID or date
    """
    try:
        from app.models import Employee
        from datetime import datetime
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Parse date if provided
        parsed_date = None
        if leave_date:
            try:
                parsed_date = datetime.strptime(leave_date, '%Y-%m-%d').date()
            except:
                return {
                    "success": False,
                    "error": "invalid_date_format",
                    "message": f"Invalid date format. Use YYYY-MM-DD"
                }
        
        # Cancel leave
        result = await LeaveAutomationService.cancel_leave_application(
            db=session,
            employee_id=employee.id,
            application_id=application_id,
            leave_date=parsed_date
        )
        
        return result
        
    except Exception as e:
        print(f"Leave cancellation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to cancel leave: {str(e)}"
        }


@router.post("/submit-wfh")
async def submit_wfh_request(
    date: str = Query(..., description="WFH date (YYYY-MM-DD)"),
    reason: str = Query(..., description="Reason for WFH"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Submit WFH (Work From Home) request
    AI chatbot calls this endpoint after collecting all required information
    """
    try:
        from app.models import Employee
        from datetime import datetime
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Parse date
        try:
            wfh_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            return {
                "success": False,
                "error": "invalid_date_format",
                "message": f"Invalid date format: {date}. Use YYYY-MM-DD"
            }
        
        # Submit WFH request
        result = await WFHAutomationService.submit_wfh_request(
            db=session,
            employee_id=employee.id,
            user_id=current_user.id,
            wfh_date=wfh_date,
            reason=reason,
            manager_id=employee.manager_id
        )
        
        return result
        
    except Exception as e:
        print(f"WFH submission error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to submit WFH request: {str(e)}"
        }


@router.post("/regularize-attendance")
async def regularize_attendance(
    date: str = Query(..., description="Date to regularize (YYYY-MM-DD)"),
    check_in: Optional[str] = Query(None, description="Check-in time (HH:MM AM/PM)"),
    check_out: Optional[str] = Query(None, description="Check-out time (HH:MM AM/PM)"),
    reason: str = Query(..., description="Reason for regularization"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Submit attendance regularization request
    AI chatbot calls this endpoint after collecting all required information
    """
    try:
        from app.models import Employee
        from datetime import datetime
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Parse date
        try:
            attendance_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            return {
                "success": False,
                "error": "invalid_date_format",
                "message": f"Invalid date format: {date}. Use YYYY-MM-DD"
            }
        
        # Submit regularization
        result = await AttendanceAutomationService.submit_regularization_request(
            db=session,
            employee_id=employee.id,
            attendance_date=attendance_date,
            check_in_time=check_in,
            check_out_time=check_out,
            reason=reason,
            manager_id=employee.manager_id
        )
        
        return result
        
    except Exception as e:
        print(f"Regularization error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to submit regularization: {str(e)}"
        }


@router.get("/balance/comprehensive")
async def get_comprehensive_balance(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get comprehensive balance information across all HR modules
    Returns unified view of leave, attendance, WFH quota, overtime, etc.
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get comprehensive balance
        balance_data = await BalanceAutomationService.get_comprehensive_balance(
            db=session,
            employee_id=employee.id
        )
        
        return balance_data
        
    except Exception as e:
        print(f"Balance fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch balance: {str(e)}"
        }


@router.get("/balance/quick-summary")
async def get_quick_balance_summary(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get quick balance summary for chatbot
    Lightweight version with just essentials
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get quick summary
        summary = await BalanceAutomationService.get_quick_balance_summary(
            db=session,
            employee_id=employee.id
        )
        
        return summary
        
    except Exception as e:
        print(f"Quick balance error: {str(e)}")
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch quick balance: {str(e)}"
        }


@router.get("/payslip/latest")
async def get_latest_payslip(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get latest payslip with complete breakdown
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get latest payslip
        payslip_data = await PayrollAutomationService.get_latest_payslip(
            db=session,
            employee_id=employee.id
        )
        
        return payslip_data
        
    except Exception as e:
        print(f"Payslip fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch payslip: {str(e)}"
        }


@router.get("/payslip/breakdown")
async def get_salary_breakdown(
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed salary breakdown with component-wise split
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get salary breakdown
        breakdown_data = await PayrollAutomationService.get_salary_breakdown(
            db=session,
            employee_id=employee.id,
            month=month
        )
        
        return breakdown_data
        
    except Exception as e:
        print(f"Breakdown fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch salary breakdown: {str(e)}"
        }


@router.get("/payslip/ytd")
async def get_ytd_summary(
    financial_year: Optional[int] = Query(None, description="Financial year (e.g., 2024)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get Year-to-Date (YTD) earnings and tax summary
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get YTD summary
        ytd_data = await PayrollAutomationService.get_ytd_summary(
            db=session,
            employee_id=employee.id,
            financial_year=financial_year
        )
        
        return ytd_data
        
    except Exception as e:
        print(f"YTD fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch YTD summary: {str(e)}"
        }


@router.get("/payslip/history")
async def get_salary_history(
    months: int = Query(6, description="Number of months", ge=1, le=12),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get salary history for last N months
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get salary history
        history_data = await PayrollAutomationService.get_salary_history(
            db=session,
            employee_id=employee.id,
            months=months
        )
        
        return history_data
        
    except Exception as e:
        print(f"History fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch salary history: {str(e)}"
        }


@router.post("/expense/calculate-mileage")
async def calculate_mileage_reimbursement(
    from_city: str,
    to_city: str,
    vehicle_type: str = "four_wheeler",
    custom_distance: Optional[float] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculate mileage reimbursement for travel
    """
    try:
        result = ExpenseAutomationService.calculate_mileage(
            from_city=from_city,
            to_city=to_city,
            vehicle_type=vehicle_type,
            custom_distance=custom_distance
        )
        
        return result
        
    except Exception as e:
        print(f"Mileage calculation error: {str(e)}")
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to calculate mileage: {str(e)}"
        }


@router.post("/expense/submit")
async def submit_expense_claim_endpoint(
    category: str,
    amount: float,
    expense_date: str,
    description: str,
    merchant: Optional[str] = None,
    has_receipt: bool = False,
    receipt_url: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Submit expense claim
    """
    try:
        from app.models import Employee
        from datetime import datetime
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Parse date
        expense_date_obj = datetime.strptime(expense_date, '%Y-%m-%d').date()
        
        # Submit claim
        result = await ExpenseAutomationService.submit_expense_claim(
            db=session,
            employee_id=employee.id,
            user_id=current_user.id,
            category=category,
            amount=amount,
            expense_date=expense_date_obj,
            description=description,
            merchant=merchant,
            has_receipt=has_receipt,
            receipt_url=receipt_url
        )
        
        return result
        
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_date",
            "message": "Invalid date format. Use YYYY-MM-DD"
        }
    except Exception as e:
        print(f"Expense submission error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to submit expense claim: {str(e)}"
        }


@router.get("/expense/summary")
async def get_expense_summary_endpoint(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get expense claims summary
    """
    try:
        from app.models import Employee
        
        # Get employee
        stmt = select(Employee).where(Employee.user_id == current_user.id)
        result = await session.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            return {
                "success": False,
                "error": "employee_not_found",
                "message": "Employee profile not found"
            }
        
        # Get summary
        summary = await ExpenseAutomationService.get_expense_summary(
            db=session,
            employee_id=employee.id,
            month=month,
            year=year
        )
        
        return summary
        
    except Exception as e:
        print(f"Expense summary error: {str(e)}")
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to fetch expense summary: {str(e)}"
        }


@router.post("/expense/categorize")
async def categorize_expense_endpoint(
    description: str,
    amount: float,
    merchant: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Auto-categorize expense based on description
    """
    try:
        result = ExpenseAutomationService.categorize_expense(
            description=description,
            amount=amount,
            merchant=merchant
        )
        
        return result
        
    except Exception as e:
        print(f"Categorization error: {str(e)}")
        return {
            "success": False,
            "error": "system_error",
            "message": f"Failed to categorize expense: {str(e)}"
        }



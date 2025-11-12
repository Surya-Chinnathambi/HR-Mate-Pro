"""
Advanced HR AI Chatbot Service with Azure OpenAI Integration
Handles conversation context, function calling, policy enforcement, and RBAC
"""
import json
import uuid
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from openai import OpenAI  # Changed from AzureOpenAI to OpenAI for LiteLLM compatibility
from sqlmodel import Session, select
from app.models.ai_chat import ConversationHistory, AIChatSession, AIFunctionCall
from app.models.user import User, UserRole, Employee
from app.models.attendance import (
    LeaveBalance, LeaveApplication, LeaveApplicationStatus,
    AttendanceDay, AttendanceStatus
)
from app.models.workflow import WorkAssignment, TaskStatus, TaskPriority, TaskComment
from app.core.security import get_current_user
from app.config import settings
import redis

# Initialize Redis client using settings
redis_client = redis.Redis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    db=settings.REDIS_DB, 
    decode_responses=True
)

# OpenAI client will be initialized lazily
openai_client = None

def get_azure_client():
    """Lazy initialization of OpenAI client for LiteLLM proxy"""
    global openai_client
    if openai_client is None:
        # Try to get API key from settings first, then environment variables
        # Handle both None and empty string cases
        api_key = (settings.AZURE_OPENAI_KEY and settings.AZURE_OPENAI_KEY.strip()) or \
                  (settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip()) or \
                  os.getenv('AZURE_OPENAI_KEY') or \
                  os.getenv('OPENAI_API_KEY')
        
        endpoint = (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_ENDPOINT.strip()) or \
                   os.getenv('AZURE_OPENAI_ENDPOINT') or \
                   "https://litellm.dev.asoclab.dev/v1"
        
        if not api_key:
            print(f"DEBUG: settings.AZURE_OPENAI_KEY = {repr(settings.AZURE_OPENAI_KEY)}")
            print(f"DEBUG: settings.OPENAI_API_KEY = {repr(settings.OPENAI_API_KEY)}")
            print(f"DEBUG: os.getenv('AZURE_OPENAI_KEY') = {repr(os.getenv('AZURE_OPENAI_KEY'))}")
            print(f"DEBUG: os.getenv('OPENAI_API_KEY') = {repr(os.getenv('OPENAI_API_KEY'))}")
            raise ValueError("Azure OpenAI API key not configured in settings or environment")
        
        # Use standard OpenAI client with custom base_url for LiteLLM proxy
        openai_client = OpenAI(
            api_key=api_key,
            base_url=endpoint
        )
    return openai_client


class HRChatbotService:
    """
    Main service for HR AI Chatbot with function calling and policy enforcement
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.system_prompt = self._load_system_prompt()
        self.functions = self._define_functions()
    
    def _load_system_prompt(self) -> str:
        """Load the comprehensive system prompt for the HR assistant"""
        return """You are an intelligent HR Assistant chatbot powered by Azure OpenAI, designed to automate HR workflows with role-based access control, company policy enforcement, and persistent conversational memory.

## Core Responsibilities:
1. Help employees with leave applications, attendance, expenses, and timesheets
2. Assist with work assignments, task management, and workload tracking
3. Enforce company policies and approval workflows
4. Provide managers with team insights, workload analytics, and assignment suggestions
5. Assist HR admins with analytics and policy configuration
6. Maintain conversation context and provide proactive suggestions

## Work Assignment Intelligence:
- When assigning tasks, automatically check employee workload and skills
- Suggest optimal assignees based on capacity, skills, and past performance
- Alert managers when team members are overloaded (>80% capacity)
- Track task progress and send smart reminders for overdue items
- Enable conversational task delegation with context preservation

## Natural Language Understanding:
- Parse task details from natural language ("Assign the API integration to John, high priority, due next Friday")
- Understand relative dates ("tomorrow", "next week", "in 3 days")
- Extract priority from keywords ("urgent", "ASAP", "when you can" = low)
- Infer required skills from task descriptions
- Handle task status updates conversationally ("mark task 123 as 50% done")

## Key Principles:
- Always check user permissions before executing actions
- Validate against company policies before submitting requests
- Provide clear explanations for policy violations
- Offer alternatives when requests cannot be fulfilled
- Log all actions for compliance and audit
- Be helpful, clear, and professional

## Response Format:
- Use emojis sparingly for visual clarity (✅, ❌, 📊, ⚠️, 📋, 🤖)
- Break down complex information into bullet points
- Always confirm before executing irreversible actions
- Provide request IDs for tracking
- Show relevant quick action buttons
- Highlight overdue tasks and overloaded team members

## Organizational Context:
- Respect reporting hierarchies (managers can assign to their team)
- Support matrix organizations (dotted-line reporting)
- Track workload across projects and initiatives
- Enable cross-functional collaboration

Remember: You're not just a bot, you're their trusted HR companion with intelligent work management capabilities."""

    def _define_functions(self) -> List[Dict[str, Any]]:
        """Define all available function calling schemas"""
        return [
            {
                "name": "applyLeave",
                "description": "Submit a leave application with automatic policy validation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "leaveTypeId": {
                            "type": "string",
                            "enum": ["sick", "casual", "earned", "wfh", "compensatory"],
                            "description": "Type of leave to apply"
                        },
                        "startDate": {
                            "type": "string",
                            "format": "date",
                            "description": "Leave start date (YYYY-MM-DD)"
                        },
                        "endDate": {
                            "type": "string",
                            "format": "date",
                            "description": "Leave end date (YYYY-MM-DD)"
                        },
                        "partialDay": {
                            "type": "boolean",
                            "description": "Whether this is a half-day leave"
                        },
                        "partialDayType": {
                            "type": "string",
                            "enum": ["first_half", "second_half"],
                            "description": "Which half of the day (required if partialDay=true)"
                        },
                        "reason": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Reason for leave (minimum 10 characters)"
                        },
                        "attachmentUrl": {
                            "type": "string",
                            "description": "Optional URL to attachment (e.g., medical certificate)"
                        },
                        "notifyBackup": {
                            "type": "boolean",
                            "description": "Whether to notify team members"
                        }
                    },
                    "required": ["leaveTypeId", "startDate", "endDate", "reason"]
                }
            },
            {
                "name": "getLeaveBalance",
                "description": "Retrieve current leave balances and accrual details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "employeeId": {
                            "type": "string",
                            "description": "Employee ID (optional, defaults to current user)"
                        },
                        "fiscalYear": {
                            "type": "string",
                            "pattern": "^\\d{4}$",
                            "description": "Fiscal year (YYYY, defaults to current)"
                        }
                    }
                }
            },
            {
                "name": "clock",
                "description": "Clock in/out with automatic location and policy validation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["in", "out"],
                            "description": "Clock in or out"
                        },
                        "latitude": {
                            "type": "number",
                            "description": "Optional latitude for geo-fencing"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Optional longitude for geo-fencing"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes for irregular timing"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "getAttendance",
                "description": "Fetch attendance records with summary statistics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fromDate": {
                            "type": "string",
                            "format": "date",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "toDate": {
                            "type": "string",
                            "format": "date",
                            "description": "End date (YYYY-MM-DD)"
                        },
                        "employeeId": {
                            "type": "string",
                            "description": "Employee ID (optional, manager/HR only)"
                        },
                        "includeRegularizations": {
                            "type": "boolean",
                            "description": "Include regularization requests (default: true)"
                        }
                    },
                    "required": ["fromDate", "toDate"]
                }
            },
            {
                "name": "submitExpense",
                "description": "Submit expense claim with auto-routing to approvers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expenseCategory": {
                            "type": "string",
                            "enum": ["travel", "food", "accommodation", "supplies", "entertainment", "other"],
                            "description": "Category of expense"
                        },
                        "amount": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Expense amount"
                        },
                        "currency": {
                            "type": "string",
                            "enum": ["USD", "EUR", "INR"],
                            "description": "Currency code (default: USD)"
                        },
                        "expenseDate": {
                            "type": "string",
                            "format": "date",
                            "description": "Date of expense (YYYY-MM-DD)"
                        },
                        "merchantName": {
                            "type": "string",
                            "description": "Name of merchant/vendor"
                        },
                        "description": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Expense description (minimum 10 characters)"
                        },
                        "receiptUrl": {
                            "type": "string",
                            "description": "URL to receipt image (required if amount > 50)"
                        },
                        "projectId": {
                            "type": "string",
                            "description": "Optional project ID for billable expenses"
                        }
                    },
                    "required": ["expenseCategory", "amount", "expenseDate", "merchantName", "description"]
                }
            },
            {
                "name": "getPendingApprovals",
                "description": "Fetch all requests awaiting approval (Manager/HR only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requestType": {
                            "type": "string",
                            "enum": ["all", "leave", "expense", "regularization", "timesheet"],
                            "description": "Type of requests to fetch"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low", "all"],
                            "description": "Priority filter"
                        }
                    }
                }
            },
            {
                "name": "approveRequest",
                "description": "Approve or reject pending requests (Manager/HR only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requestType": {
                            "type": "string",
                            "enum": ["leave", "expense", "regularization", "timesheet"],
                            "description": "Type of request"
                        },
                        "requestId": {
                            "type": "string",
                            "description": "Unique request ID"
                        },
                        "decision": {
                            "type": "string",
                            "enum": ["approve", "reject", "request_info"],
                            "description": "Approval decision"
                        },
                        "comments": {
                            "type": "string",
                            "description": "Comments (required if reject)"
                        }
                    },
                    "required": ["requestType", "requestId", "decision"]
                }
            },
            {
                "name": "getPayslips",
                "description": "Retrieve payslip documents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "pattern": "^\\d{4}-\\d{2}$",
                            "description": "Period in YYYY-MM format"
                        },
                        "employeeId": {
                            "type": "string",
                            "description": "Employee ID (optional, HR only)"
                        },
                        "includeYTD": {
                            "type": "boolean",
                            "description": "Include year-to-date summary"
                        }
                    }
                }
            },
            # 5 EXTRA FUNCTIONS
            {
                "name": "getTeamStatus",
                "description": "Get real-time status of team members (Manager only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date to check (defaults to today)"
                        },
                        "includeLeaves": {
                            "type": "boolean",
                            "description": "Include upcoming leaves"
                        }
                    }
                }
            },
            {
                "name": "getMyDocuments",
                "description": "Retrieve employee documents like offer letter, payslips, tax forms",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "documentType": {
                            "type": "string",
                            "enum": ["all", "offer_letter", "appointment_letter", "payslips", "tax_forms", "id_proof", "certificates"],
                            "description": "Type of document to retrieve"
                        },
                        "year": {
                            "type": "string",
                            "description": "Filter by year (YYYY)"
                        }
                    }
                }
            },
            {
                "name": "applyWorkFromHome",
                "description": "Apply for work from home (WFH) request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "WFH date (YYYY-MM-DD)"
                        },
                        "reason": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Reason for WFH"
                        },
                        "fullDay": {
                            "type": "boolean",
                            "description": "Full day or partial (default: true)"
                        }
                    },
                    "required": ["date", "reason"]
                }
            },
            {
                "name": "getHolidays",
                "description": "Get list of company holidays and optional holidays",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "string",
                            "pattern": "^\\d{4}$",
                            "description": "Year (YYYY, defaults to current)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Office location filter (optional)"
                        },
                        "includeOptional": {
                            "type": "boolean",
                            "description": "Include optional holidays"
                        }
                    }
                }
            },
            {
                "name": "requestAttendanceRegularization",
                "description": "Request regularization for missed clock in/out",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date to regularize (YYYY-MM-DD)"
                        },
                        "checkInTime": {
                            "type": "string",
                            "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$",
                            "description": "Check-in time (HH:MM format)"
                        },
                        "checkOutTime": {
                            "type": "string",
                            "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$",
                            "description": "Check-out time (HH:MM format)"
                        },
                        "reason": {
                            "type": "string",
                            "minLength": 15,
                            "description": "Detailed reason for regularization (minimum 15 characters)"
                        }
                    },
                    "required": ["date", "checkInTime", "checkOutTime", "reason"]
                }
            },
            # ============================================================================
            # WORK ASSIGNMENT FUNCTIONS (NEW - Phase 4)
            # ============================================================================
            {
                "name": "assignWork",
                "description": "Assign a task or work item to an employee with AI-powered validation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "minLength": 5,
                            "maxLength": 200,
                            "description": "Brief task title (5-200 characters)"
                        },
                        "description": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Detailed task description with requirements and deliverables"
                        },
                        "assigneeId": {
                            "type": "integer",
                            "description": "Employee ID to assign task to"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority level"
                        },
                        "dueDate": {
                            "type": "string",
                            "format": "date",
                            "description": "Task due date (YYYY-MM-DD)"
                        },
                        "estimatedHours": {
                            "type": "number",
                            "minimum": 0.5,
                            "maximum": 200,
                            "description": "Estimated hours to complete"
                        },
                        "projectName": {
                            "type": "string",
                            "description": "Optional project name this task belongs to"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags/skills required (e.g., ['python', 'api', 'frontend'])"
                        }
                    },
                    "required": ["title", "description", "assigneeId", "priority"]
                }
            },
            {
                "name": "getMyTasks",
                "description": "Retrieve tasks assigned to the current user with filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["all", "not_started", "in_progress", "blocked", "under_review", "completed"],
                            "description": "Filter by task status (default: all active)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["all", "low", "medium", "high", "urgent"],
                            "description": "Filter by priority"
                        },
                        "includeCompleted": {
                            "type": "boolean",
                            "description": "Include completed tasks (default: false)"
                        },
                        "sortBy": {
                            "type": "string",
                            "enum": ["due_date", "priority", "created_at"],
                            "description": "Sort order (default: due_date)"
                        }
                    }
                }
            },
            {
                "name": "updateTaskStatus",
                "description": "Update task status and progress percentage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "taskId": {
                            "type": "integer",
                            "description": "Work assignment ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["not_started", "in_progress", "blocked", "under_review", "completed", "cancelled"],
                            "description": "New status"
                        },
                        "progress": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Progress percentage (0-100)"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Optional comment about status change"
                        }
                    },
                    "required": ["taskId", "status"]
                }
            },
            {
                "name": "getTeamWorkload",
                "description": "Get team workload and capacity analysis (Manager only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "includeDetails": {
                            "type": "boolean",
                            "description": "Include detailed task breakdown per employee"
                        },
                        "onlyOverloaded": {
                            "type": "boolean",
                            "description": "Show only overloaded employees (>80% capacity)"
                        },
                        "onlyAvailable": {
                            "type": "boolean",
                            "description": "Show only available employees (<60% capacity)"
                        }
                    }
                }
            },
            {
                "name": "delegateTask",
                "description": "Reassign/delegate a task to another employee",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "taskId": {
                            "type": "integer",
                            "description": "Work assignment ID to delegate"
                        },
                        "newAssigneeId": {
                            "type": "integer",
                            "description": "Employee ID to delegate to"
                        },
                        "reason": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Reason for delegation (minimum 10 characters)"
                        },
                        "notifyBoth": {
                            "type": "boolean",
                            "description": "Notify both old and new assignee (default: true)"
                        }
                    },
                    "required": ["taskId", "newAssigneeId", "reason"]
                }
            },
            {
                "name": "suggestWorkAssignment",
                "description": "Get AI-powered employee suggestions for task assignment based on skills and workload",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "taskDescription": {
                            "type": "string",
                            "description": "Description of the task to assign"
                        },
                        "requiredSkills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Skills required for the task"
                        },
                        "estimatedHours": {
                            "type": "number",
                            "description": "Estimated hours for the task"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority"
                        },
                        "topN": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Number of suggestions to return (default: 3)"
                        }
                    },
                    "required": ["taskDescription"]
                }
            },
            {
                "name": "sendBroadcastMessage",
                "description": "Send a broadcast message to specific recipient groups (all employees, all managers, specific teams, or custom recipients)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message content to broadcast"
                        },
                        "recipientType": {
                            "type": "string",
                            "enum": ["all_employees", "all_managers", "specific_teams", "custom"],
                            "description": "Type of recipients for the broadcast"
                        },
                        "recipientIds": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of employee IDs (for custom) or team IDs (for specific_teams)"
                        },
                        "scheduledTime": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Optional: Schedule the broadcast for a future time (ISO 8601 format)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Message priority level (default: medium)"
                        },
                        "templateUsed": {
                            "type": "string",
                            "description": "Optional: Name of template used"
                        }
                    },
                    "required": ["message", "recipientType"]
                }
            }
        ]
    
    async def chat(
        self, 
        user_message: str, 
        user: User, 
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main chat interface - processes user message and returns bot response
        """
        # Create or retrieve conversation ID
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Get conversation context from Redis
        context = await self._get_conversation_context(conversation_id, user.id)
        
        # Save user message
        await self._save_message(
            conversation_id=conversation_id,
            user_id=user.id,
            role=user.role,
            message_type="user_message",
            message_text=user_message
        )
        
        # Prepare messages for OpenAI
        messages = [
            {"role": "system", "content": self.system_prompt},
            *context.get("last_10_messages", []),
            {"role": "user", "content": user_message}
        ]
        
        # Call Azure OpenAI with function calling
        try:
            client = get_azure_client()
            response = client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                functions=self.functions,
                function_call="auto",
                temperature=1,  # GPT-5 only supports temperature=1
                max_tokens=800
            )
            
            message = response.choices[0].message
            
            # Check if function call is needed
            if message.function_call:
                function_name = message.function_call.name
                function_args = json.loads(message.function_call.arguments)
                
                # Execute function with RBAC and policy checks
                function_result = await self._execute_function(
                    function_name=function_name,
                    arguments=function_args,
                    user=user,
                    conversation_id=conversation_id
                )
                
                # Get final response from AI with function result
                messages.append(message.model_dump())
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_result)
                })
                
                final_response = client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT,
                    messages=messages,
                    temperature=1,  # GPT-5 only supports temperature=1
                    max_tokens=800
                )
                
                bot_message = final_response.choices[0].message.content
            else:
                bot_message = message.content
            
            # Save bot response
            await self._save_message(
                conversation_id=conversation_id,
                user_id=user.id,
                role=user.role,
                message_type="bot_response",
                message_text=bot_message,
                function_called=message.function_call.name if message.function_call else None,
                function_params=message.function_call.arguments if message.function_call else None
            )
            
            # Update Redis context
            await self._update_conversation_context(
                conversation_id=conversation_id,
                user_id=user.id,
                new_messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": bot_message}
                ]
            )
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "message": bot_message,
                "function_called": message.function_call.name if message.function_call else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_message = f"I encountered an error: {str(e)}. Please try again or contact HR support."
            
            await self._save_message(
                conversation_id=conversation_id,
                user_id=user.id,
                role=user.role,
                message_type="bot_response",
                message_text=error_message,
                action_status="failed",
                metadata={"error": str(e)}
            )
            
            return {
                "success": False,
                "conversation_id": conversation_id,
                "message": error_message,
                "function_called": None,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _execute_function(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        user: User,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Execute requested function with RBAC and policy validation
        """
        start_time = datetime.utcnow()
        
        try:
            # RBAC check
            if not await self._check_permissions(function_name, user):
                return {
                    "success": False,
                    "error": f"You don't have permission to perform this action. Required role: {self._get_required_role(function_name)}"
                }
            
            # Route to appropriate handler
            if function_name == "applyLeave":
                result = await self._handle_apply_leave(arguments, user)
            elif function_name == "getLeaveBalance":
                result = await self._handle_get_leave_balance(arguments, user)
            elif function_name == "clock":
                result = await self._handle_clock(arguments, user)
            elif function_name == "getAttendance":
                result = await self._handle_get_attendance(arguments, user)
            elif function_name == "submitExpense":
                result = await self._handle_submit_expense(arguments, user)
            elif function_name == "getPendingApprovals":
                result = await self._handle_get_pending_approvals(arguments, user)
            elif function_name == "approveRequest":
                result = await self._handle_approve_request(arguments, user)
            elif function_name == "getPayslips":
                result = await self._handle_get_payslips(arguments, user)
            elif function_name == "getTeamStatus":
                result = await self._handle_get_team_status(arguments, user)
            elif function_name == "getMyDocuments":
                result = await self._handle_get_my_documents(arguments, user)
            elif function_name == "applyWorkFromHome":
                result = await self._handle_apply_work_from_home(arguments, user)
            elif function_name == "getHolidays":
                result = await self._handle_get_holidays(arguments, user)
            elif function_name == "requestAttendanceRegularization":
                result = await self._handle_request_attendance_regularization(arguments, user)
            # Work assignment handlers (Phase 4)
            elif function_name == "assignWork":
                result = await self._handle_assign_work(arguments, user)
            elif function_name == "getMyTasks":
                result = await self._handle_get_my_tasks(arguments, user)
            elif function_name == "updateTaskStatus":
                result = await self._handle_update_task_status(arguments, user)
            elif function_name == "getTeamWorkload":
                result = await self._handle_get_team_workload(arguments, user)
            elif function_name == "delegateTask":
                result = await self._handle_delegate_task(arguments, user)
            elif function_name == "suggestWorkAssignment":
                result = await self._handle_suggest_work_assignment(arguments, user)
            elif function_name == "sendBroadcastMessage":
                result = await self._handle_send_broadcast_message(arguments, user)
            else:
                result = {"success": False, "error": f"Unknown function: {function_name}"}
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log function call
            await self._log_function_call(
                conversation_id=conversation_id,
                user_id=user.id,
                function_name=function_name,
                parameters=arguments,
                response=result,
                status="success" if result.get("success") else "failed",
                execution_time_ms=int(execution_time)
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            await self._log_function_call(
                conversation_id=conversation_id,
                user_id=user.id,
                function_name=function_name,
                parameters=arguments,
                response=None,
                status="failed",
                execution_time_ms=int(execution_time),
                error_message=str(e)
            )
            
            return {
                "success": False,
                "error": f"Function execution failed: {str(e)}"
            }
    
    async def _check_permissions(self, function_name: str, user: User) -> bool:
        """Check if user has permission to call this function"""
        # Define permission mapping
        employee_functions = [
            "applyLeave", "getLeaveBalance", "clock", "getAttendance", 
            "submitExpense", "getPayslips", "getMyDocuments", "applyWorkFromHome",
            "getHolidays", "requestAttendanceRegularization",
            # Work assignment functions for employees
            "getMyTasks", "updateTaskStatus", "delegateTask"
        ]
        manager_functions = employee_functions + [
            "getPendingApprovals", "approveRequest", "getTeamStatus",
            # Work assignment functions for managers
            "assignWork", "getTeamWorkload", "suggestWorkAssignment"
        ]
        hr_admin_functions = manager_functions + [
            "configureLeavePolicy", 
            "generateReport",
            # Broadcast messaging - HR only
            "sendBroadcastMessage"
        ]
        
        if user.role == UserRole.EMPLOYEE:
            return function_name in employee_functions
        elif user.role == UserRole.MANAGER:
            return function_name in manager_functions
        elif user.role == UserRole.HR or user.role == "super_admin":
            return True  # HR and super_admin have full access
        
        return False
    
    def _get_required_role(self, function_name: str) -> str:
        """Get minimum required role for a function"""
        if function_name in ["getPendingApprovals", "approveRequest"]:
            return "Manager"
        elif function_name in ["configureLeavePolicy", "generateReport", "sendBroadcastMessage"]:
            return "HR Admin"
        return "Employee"
    
    # Context Management
    async def _get_conversation_context(self, conversation_id: str, user_id: int) -> Dict[str, Any]:
        """Retrieve conversation context from Redis"""
        cache_key = f"conv:{conversation_id}:context"
        cached_context = redis_client.get(cache_key)
        
        if cached_context:
            return json.loads(cached_context)
        
        # If not in cache, load from PostgreSQL
        stmt = select(ConversationHistory).where(
            ConversationHistory.conversation_id == uuid.UUID(conversation_id)
        ).order_by(ConversationHistory.created_at.desc()).limit(10)
        
        messages = self.session.exec(stmt).all()
        
        context = {
            "user_id": user_id,
            "last_10_messages": [
                {
                    "role": "user" if msg.message_type == "user_message" else "assistant",
                    "content": msg.message_text
                }
                for msg in reversed(messages)
            ],
            "session_start": datetime.utcnow().isoformat()
        }
        
        # Cache for 24 hours
        redis_client.setex(cache_key, 86400, json.dumps(context))
        
        return context
    
    async def _update_conversation_context(
        self, 
        conversation_id: str, 
        user_id: int, 
        new_messages: List[Dict[str, str]]
    ):
        """Update Redis cache with new messages"""
        cache_key = f"conv:{conversation_id}:context"
        context = await self._get_conversation_context(conversation_id, user_id)
        
        context["last_10_messages"].extend(new_messages)
        context["last_10_messages"] = context["last_10_messages"][-10:]  # Keep only last 10
        
        redis_client.setex(cache_key, 86400, json.dumps(context))
    
    async def _save_message(
        self,
        conversation_id: str,
        user_id: int,
        role: str,
        message_type: str,
        message_text: str,
        intent: Optional[str] = None,
        function_called: Optional[str] = None,
        function_params: Optional[Dict] = None,
        action_status: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Save message to PostgreSQL"""
        message = ConversationHistory(
            conversation_id=uuid.UUID(conversation_id),
            user_id=user_id,
            role=role,
            message_type=message_type,
            message_text=message_text,
            intent=intent,
            function_called=function_called,
            function_params=function_params,
            action_status=action_status,
            metadata=metadata
        )
        
        self.session.add(message)
        self.session.commit()
    
    async def _log_function_call(
        self,
        conversation_id: str,
        user_id: int,
        function_name: str,
        parameters: Dict[str, Any],
        response: Optional[Dict[str, Any]],
        status: str,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Log function call for audit"""
        function_call = AIFunctionCall(
            conversation_id=uuid.UUID(conversation_id),
            user_id=user_id,
            function_name=function_name,
            parameters=parameters,
            response=response,
            status=status,
            execution_time_ms=execution_time_ms,
            error_message=error_message
        )
        
        self.session.add(function_call)
        self.session.commit()
    
    # Function Handlers - Real Business Logic Implementation
    async def _handle_apply_leave(self, args: Dict, user: User) -> Dict:
        """Handle leave application"""
        try:
            # Get employee record
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Parse dates
            from_date = datetime.strptime(args["from_date"], "%Y-%m-%d").date()
            to_date = datetime.strptime(args["to_date"], "%Y-%m-%d").date()
            
            if from_date > to_date:
                return {"success": False, "error": "From date cannot be after to date"}
            
            # Calculate number of days
            days_requested = (to_date - from_date).days + 1
            
            # Check leave balance
            leave_balance = self.session.exec(
                select(LeaveBalance).where(
                    LeaveBalance.employee_id == employee.id,
                    LeaveBalance.leave_type == args["leave_type"]
                )
            ).first()
            
            if not leave_balance or leave_balance.balance < days_requested:
                return {
                    "success": False,
                    "error": f"Insufficient {args['leave_type']} leave balance. Available: {leave_balance.balance if leave_balance else 0} days, Requested: {days_requested} days"
                }
            
            # Create leave application
            leave_app = LeaveApplication(
                employee_id=employee.id,
                leave_type=args["leave_type"],
                from_date=from_date,
                to_date=to_date,
                days_count=days_requested,
                reason=args.get("reason", ""),
                status=LeaveApplicationStatus.PENDING
            )
            
            self.session.add(leave_app)
            self.session.commit()
            self.session.refresh(leave_app)
            
            return {
                "success": True,
                "leaveRequestId": f"LV-{leave_app.id}",
                "status": "pending_approval",
                "days_requested": days_requested,
                "from_date": str(from_date),
                "to_date": str(to_date),
                "message": f"Leave request for {days_requested} day(s) submitted successfully and pending manager approval"
            }
            
        except ValueError as e:
            return {"success": False, "error": f"Invalid date format. Use YYYY-MM-DD format. {str(e)}"}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to apply leave: {str(e)}"}
    
    async def _handle_get_leave_balance(self, args: Dict, user: User) -> Dict:
        """Handle leave balance query"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Get all leave balances
            query = select(LeaveBalance).where(LeaveBalance.employee_id == employee.id)
            
            # Filter by specific leave type if provided
            if args.get("leave_type"):
                query = query.where(LeaveBalance.leave_type == args["leave_type"])
            
            leave_balances = self.session.exec(query).all()
            
            if not leave_balances:
                return {
                    "success": True,
                    "balances": {},
                    "message": "No leave balances found. Please contact HR."
                }
            
            balances = {}
            for lb in leave_balances:
                balances[lb.leave_type] = {
                    "allocated": lb.allocated,
                    "used": lb.used,
                    "balance": lb.balance
                }
            
            return {
                "success": True,
                "employee_name": employee.display_name,
                "balances": balances,
                "message": f"Leave balances retrieved successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get leave balance: {str(e)}"}
    
    async def _handle_clock(self, args: Dict, user: User) -> Dict:
        """Handle clock in/out"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            action = args["action"]
            today = date.today()
            current_time = datetime.now()
            
            # Check if attendance record exists for today
            attendance = self.session.exec(
                select(AttendanceDay).where(
                    AttendanceDay.employee_id == employee.id,
                    AttendanceDay.date == today
                )
            ).first()
            
            if action == "clock_in":
                if attendance and attendance.check_in_time:
                    return {
                        "success": False,
                        "error": f"Already clocked in today at {attendance.check_in_time.strftime('%H:%M:%S')}"
                    }
                
                if not attendance:
                    attendance = AttendanceDay(
                        employee_id=employee.id,
                        date=today,
                        check_in_time=current_time,
                        status=AttendanceStatus.PRESENT,
                        source="chatbot"
                    )
                    self.session.add(attendance)
                else:
                    attendance.check_in_time = current_time
                    attendance.status = AttendanceStatus.PRESENT
                
                self.session.commit()
                self.session.refresh(attendance)
                
                return {
                    "success": True,
                    "action": "clock_in",
                    "timestamp": current_time.isoformat(),
                    "location": args.get("location", "Not specified"),
                    "message": f"✅ Clocked in successfully at {current_time.strftime('%H:%M:%S')}"
                }
            
            elif action == "clock_out":
                if not attendance or not attendance.check_in_time:
                    return {
                        "success": False,
                        "error": "You haven't clocked in today. Please clock in first."
                    }
                
                if attendance.check_out_time:
                    return {
                        "success": False,
                        "error": f"Already clocked out today at {attendance.check_out_time.strftime('%H:%M:%S')}"
                    }
                
                attendance.check_out_time = current_time
                
                # Calculate work hours
                work_duration = current_time - attendance.check_in_time
                work_hours = work_duration.total_seconds() / 3600
                attendance.work_hours = round(work_hours, 2)
                
                self.session.commit()
                self.session.refresh(attendance)
                
                return {
                    "success": True,
                    "action": "clock_out",
                    "timestamp": current_time.isoformat(),
                    "work_hours": attendance.work_hours,
                    "check_in": attendance.check_in_time.strftime('%H:%M:%S'),
                    "check_out": current_time.strftime('%H:%M:%S'),
                    "message": f"✅ Clocked out successfully. Total work hours: {attendance.work_hours:.2f}"
                }
            else:
                return {"success": False, "error": "Invalid action. Use 'clock_in' or 'clock_out'"}
                
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to clock {action}: {str(e)}"}
    
    async def _handle_get_attendance(self, args: Dict, user: User) -> Dict:
        """Handle attendance query"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Parse date range
            from_date = datetime.strptime(args.get("from_date", str(date.today().replace(day=1))), "%Y-%m-%d").date()
            to_date = datetime.strptime(args.get("to_date", str(date.today())), "%Y-%m-%d").date()
            
            # Check if manager requesting team attendance
            employee_id = employee.id
            if args.get("employee_id") and user.role in ["MANAGER", "HR"]:
                target_employee = self.session.exec(
                    select(Employee).where(Employee.employee_id == args["employee_id"])
                ).first()
                if target_employee:
                    employee_id = target_employee.id
            
            # Query attendance records
            attendance_records = self.session.exec(
                select(AttendanceDay).where(
                    AttendanceDay.employee_id == employee_id,
                    AttendanceDay.date >= from_date,
                    AttendanceDay.date <= to_date
                ).order_by(AttendanceDay.date.desc())
            ).all()
            
            # Calculate summary
            present = sum(1 for a in attendance_records if a.status == AttendanceStatus.PRESENT)
            absent = sum(1 for a in attendance_records if a.status == AttendanceStatus.ABSENT)
            on_leave = sum(1 for a in attendance_records if a.status == AttendanceStatus.LEAVE)
            total_hours = sum(a.work_hours or 0 for a in attendance_records)
            
            records = []
            for att in attendance_records[:10]:  # Limit to last 10 records
                records.append({
                    "date": str(att.date),
                    "status": att.status.value,
                    "check_in": att.check_in_time.strftime('%H:%M:%S') if att.check_in_time else None,
                    "check_out": att.check_out_time.strftime('%H:%M:%S') if att.check_out_time else None,
                    "work_hours": att.work_hours
                })
            
            return {
                "success": True,
                "from_date": str(from_date),
                "to_date": str(to_date),
                "records": records,
                "summary": {
                    "present": present,
                    "absent": absent,
                    "on_leave": on_leave,
                    "total_hours": round(total_hours, 2)
                },
                "message": f"Attendance records from {from_date} to {to_date}"
            }
            
        except ValueError as e:
            return {"success": False, "error": f"Invalid date format. Use YYYY-MM-DD. {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to get attendance: {str(e)}"}
    
    async def _handle_submit_expense(self, args: Dict, user: User) -> Dict:
        """Handle expense submission"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # For now, return success with expense ID
            # Full implementation would create expense record in database
            expense_id = f"EXP-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
            
            return {
                "success": True,
                "expenseId": expense_id,
                "amount": args["amount"],
                "category": args["category"],
                "status": "pending_approval",
                "message": f"Expense claim of {args['amount']} {args.get('currency', 'INR')} for {args['category']} submitted successfully. It will be reviewed by your manager."
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to submit expense: {str(e)}"}
    
    async def _handle_get_pending_approvals(self, args: Dict, user: User) -> Dict:
        """Handle pending approvals query"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            if user.role not in ["MANAGER", "HR"]:
                return {"success": False, "error": "Only managers and HR can view pending approvals"}
            
            # Get pending leave applications for team members
            pending_leaves = self.session.exec(
                select(LeaveApplication).join(
                    Employee, LeaveApplication.employee_id == Employee.id
                ).where(
                    LeaveApplication.status == LeaveApplicationStatus.PENDING,
                    Employee.manager_id == employee.id if user.role == "MANAGER" else True
                ).order_by(LeaveApplication.created_at.desc())
            ).all()
            
            approvals = []
            for leave in pending_leaves:
                requester = self.session.get(Employee, leave.employee_id)
                approvals.append({
                    "id": leave.id,
                    "type": "leave",
                    "employee_name": requester.display_name if requester else "Unknown",
                    "employee_id": requester.employee_id if requester else "Unknown",
                    "leave_type": leave.leave_type,
                    "from_date": str(leave.from_date),
                    "to_date": str(leave.to_date),
                    "days": leave.days_count,
                    "reason": leave.reason,
                    "requested_on": leave.created_at.strftime("%Y-%m-%d %H:%M")
                })
            
            return {
                "success": True,
                "approvals": approvals,
                "count": len(approvals),
                "message": f"Found {len(approvals)} pending approval(s)"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get pending approvals: {str(e)}"}
    
    async def _handle_approve_request(self, args: Dict, user: User) -> Dict:
        """Handle request approval/rejection"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            if user.role not in ["MANAGER", "HR"]:
                return {"success": False, "error": "Only managers and HR can approve requests"}
            
            request_type = args.get("request_type", "leave")
            action = args["action"]  # approve or reject
            
            if request_type == "leave":
                leave_app = self.session.get(LeaveApplication, args["request_id"])
                
                if not leave_app:
                    return {"success": False, "error": "Leave application not found"}
                
                if leave_app.status != LeaveApplicationStatus.PENDING:
                    return {"success": False, "error": f"Leave application is already {leave_app.status.value}"}
                
                # Check if user has permission to approve
                requester = self.session.get(Employee, leave_app.employee_id)
                if user.role == "MANAGER" and requester.manager_id != employee.id:
                    return {"success": False, "error": "You can only approve requests from your team members"}
                
                if action.lower() == "approve":
                    leave_app.status = LeaveApplicationStatus.APPROVED
                    leave_app.approved_by_id = employee.id
                    leave_app.approved_at = datetime.now()
                    leave_app.comments = args.get("comments", "Approved")
                    
                    # Deduct from leave balance
                    leave_balance = self.session.exec(
                        select(LeaveBalance).where(
                            LeaveBalance.employee_id == leave_app.employee_id,
                            LeaveBalance.leave_type == leave_app.leave_type
                        )
                    ).first()
                    
                    if leave_balance:
                        leave_balance.used += leave_app.days_count
                        leave_balance.balance = leave_balance.allocated - leave_balance.used
                    
                    message = f"Leave request approved successfully. {leave_app.days_count} day(s) deducted from {leave_app.leave_type} leave balance."
                    
                elif action.lower() == "reject":
                    leave_app.status = LeaveApplicationStatus.REJECTED
                    leave_app.approved_by_id = employee.id
                    leave_app.approved_at = datetime.now()
                    leave_app.comments = args.get("comments", "Rejected")
                    message = "Leave request rejected successfully."
                else:
                    return {"success": False, "error": "Invalid action. Use 'approve' or 'reject'"}
                
                self.session.commit()
                self.session.refresh(leave_app)
                
                return {
                    "success": True,
                    "requestId": leave_app.id,
                    "decision": action,
                    "status": leave_app.status.value,
                    "message": message
                }
            
            return {"success": False, "error": "Unsupported request type"}
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to {action} request: {str(e)}"}
    
    async def _handle_get_payslips(self, args: Dict, user: User) -> Dict:
        """Handle payslip retrieval"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Note: Payroll model import needed at top
            from app.models.leave import Payroll
            
            # Get payslips for specified period
            query = select(Payroll).where(Payroll.employee_id == employee.id)
            
            if args.get("month"):
                query = query.where(Payroll.month == args["month"])
            if args.get("year"):
                query = query.where(Payroll.year == args["year"])
            
            payslips = self.session.exec(query.order_by(Payroll.year.desc(), Payroll.month.desc())).all()
            
            if not payslips:
                return {
                    "success": True,
                    "payslips": [],
                    "message": "No payslips found for the specified period"
                }
            
            payslip_data = []
            for ps in payslips[:6]:  # Last 6 months
                payslip_data.append({
                    "id": ps.id,
                    "month": ps.month,
                    "year": ps.year,
                    "gross_salary": float(ps.gross_salary) if ps.gross_salary else 0,
                    "net_salary": float(ps.net_salary) if ps.net_salary else 0,
                    "status": ps.status
                })
            
            return {
                "success": True,
                "payslips": payslip_data,
                "count": len(payslip_data),
                "message": f"Retrieved {len(payslip_data)} payslip(s)"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get payslips: {str(e)}"}
    
    # 5 EXTRA FUNCTION HANDLERS
    async def _handle_get_team_status(self, args: Dict, user: User) -> Dict:
        """Get real-time status of team members (Manager only)"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            if user.role not in ["MANAGER", "HR"]:
                return {"success": False, "error": "Only managers and HR can view team status"}
            
            # Get team members
            team_members_query = select(Employee).where(
                Employee.manager_id == employee.id if user.role == "MANAGER" else True,
                Employee.is_active == True
            )
            team_members = self.session.exec(team_members_query).all()
            
            today = date.today()
            check_date = datetime.strptime(args.get("date", str(today)), "%Y-%m-%d").date() if args.get("date") else today
            
            team_status = []
            for member in team_members:
                # Check attendance
                attendance = self.session.exec(
                    select(AttendanceDay).where(
                        AttendanceDay.employee_id == member.id,
                        AttendanceDay.date == check_date
                    )
                ).first()
                
                # Check leave
                on_leave = self.session.exec(
                    select(LeaveApplication).where(
                        LeaveApplication.employee_id == member.id,
                        LeaveApplication.from_date <= check_date,
                        LeaveApplication.to_date >= check_date,
                        LeaveApplication.status == LeaveApplicationStatus.APPROVED
                    )
                ).first()
                
                status = "Not clocked in"
                if on_leave:
                    status = f"On {on_leave.leave_type} leave"
                elif attendance:
                    if attendance.check_out_time:
                        status = f"Clocked out at {attendance.check_out_time.strftime('%H:%M')}"
                    elif attendance.check_in_time:
                        status = f"Clocked in at {attendance.check_in_time.strftime('%H:%M')}"
                
                team_status.append({
                    "employee_id": member.employee_id,
                    "name": member.display_name,
                    "designation": member.designation,
                    "status": status,
                    "on_leave": bool(on_leave)
                })
            
            return {
                "success": True,
                "date": str(check_date),
                "team_size": len(team_status),
                "team_status": team_status,
                "message": f"Team status for {check_date}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get team status: {str(e)}"}
    
    async def _handle_get_my_documents(self, args: Dict, user: User) -> Dict:
        """Retrieve employee documents"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            doc_type = args.get("documentType", "all")
            
            # Simulated document list (in real system, query from documents table)
            documents = []
            
            if doc_type in ["all", "offer_letter"]:
                documents.append({
                    "type": "offer_letter",
                    "name": "Offer Letter",
                    "date": employee.date_of_joining.strftime("%Y-%m-%d") if employee.date_of_joining else None,
                    "status": "available",
                    "download_url": f"/api/documents/offer_letter/{employee.employee_id}"
                })
            
            if doc_type in ["all", "payslips"]:
                documents.append({
                    "type": "payslips",
                    "name": "Payslips (Last 6 months)",
                    "count": 6,
                    "status": "available",
                    "download_url": f"/api/documents/payslips/{employee.employee_id}"
                })
            
            return {
                "success": True,
                "employee_name": employee.display_name,
                "documents": documents,
                "message": f"Found {len(documents)} document(s)"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get documents: {str(e)}"}
    
    async def _handle_apply_work_from_home(self, args: Dict, user: User) -> Dict:
        """Apply for work from home (WFH) request"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            wfh_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
            
            if wfh_date < date.today():
                return {"success": False, "error": "Cannot apply WFH for past dates"}
            
            # Check if already on leave that day
            existing_leave = self.session.exec(
                select(LeaveApplication).where(
                    LeaveApplication.employee_id == employee.id,
                    LeaveApplication.from_date <= wfh_date,
                    LeaveApplication.to_date >= wfh_date,
                    LeaveApplication.status.in_([LeaveApplicationStatus.PENDING, LeaveApplicationStatus.APPROVED])
                )
            ).first()
            
            if existing_leave:
                return {"success": False, "error": f"You already have a leave application for this date (Status: {existing_leave.status.value})"}
            
            # Create WFH request (as a special leave type)
            wfh_request = LeaveApplication(
                employee_id=employee.id,
                leave_type="wfh",
                from_date=wfh_date,
                to_date=wfh_date,
                days_count=1 if args.get("fullDay", True) else 0.5,
                reason=args["reason"],
                status=LeaveApplicationStatus.PENDING
            )
            
            self.session.add(wfh_request)
            self.session.commit()
            self.session.refresh(wfh_request)
            
            return {
                "success": True,
                "wfh_request_id": f"WFH-{wfh_request.id}",
                "date": str(wfh_date),
                "status": "pending_approval",
                "message": f"Work from home request for {wfh_date} submitted successfully"
            }
            
        except ValueError as e:
            return {"success": False, "error": f"Invalid date format. Use YYYY-MM-DD. {str(e)}"}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to apply WFH: {str(e)}"}
    
    async def _handle_get_holidays(self, args: Dict, user: User) -> Dict:
        """Get list of company holidays"""
        try:
            from app.models.leave import Holiday
            
            year = int(args.get("year", datetime.now().year))
            
            query = select(Holiday).where(Holiday.year == year)
            
            if args.get("location"):
                query = query.where(Holiday.location == args["location"])
            
            holidays = self.session.exec(query.order_by(Holiday.date)).all()
            
            holiday_list = []
            for holiday in holidays:
                if not args.get("includeOptional", True) and holiday.is_optional:
                    continue
                    
                holiday_list.append({
                    "date": str(holiday.date),
                    "name": holiday.name,
                    "day": holiday.date.strftime("%A"),
                    "is_optional": holiday.is_optional,
                    "location": holiday.location if hasattr(holiday, 'location') else "All"
                })
            
            return {
                "success": True,
                "year": year,
                "holidays": holiday_list,
                "count": len(holiday_list),
                "message": f"Found {len(holiday_list)} holiday(s) for {year}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get holidays: {str(e)}"}
    
    async def _handle_request_attendance_regularization(self, args: Dict, user: User) -> Dict:
        """Request regularization for missed clock in/out"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            reg_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
            
            if reg_date > date.today():
                return {"success": False, "error": "Cannot regularize future dates"}
            
            if (date.today() - reg_date).days > 7:
                return {"success": False, "error": "Cannot regularize attendance older than 7 days"}
            
            # Check if attendance exists
            attendance = self.session.exec(
                select(AttendanceDay).where(
                    AttendanceDay.employee_id == employee.id,
                    AttendanceDay.date == reg_date
                )
            ).first()
            
            check_in_time = datetime.strptime(f"{reg_date} {args['checkInTime']}", "%Y-%m-%d %H:%M")
            check_out_time = datetime.strptime(f"{reg_date} {args['checkOutTime']}", "%Y-%m-%d %H:%M")
            
            if check_in_time >= check_out_time:
                return {"success": False, "error": "Check-out time must be after check-in time"}
            
            work_hours = (check_out_time - check_in_time).total_seconds() / 3600
            
            if not attendance:
                # Create new attendance record with regularization flag
                attendance = AttendanceDay(
                    employee_id=employee.id,
                    date=reg_date,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    work_hours=round(work_hours, 2),
                    status=AttendanceStatus.PRESENT,
                    source="regularization",
                    notes=args["reason"]
                )
                self.session.add(attendance)
            else:
                # Update existing attendance
                attendance.check_in_time = check_in_time
                attendance.check_out_time = check_out_time
                attendance.work_hours = round(work_hours, 2)
                attendance.notes = f"Regularized: {args['reason']}"
            
            self.session.commit()
            self.session.refresh(attendance)
            
            return {
                "success": True,
                "regularization_id": f"REG-{attendance.id}",
                "date": str(reg_date),
                "check_in": args["checkInTime"],
                "check_out": args["checkOutTime"],
                "work_hours": round(work_hours, 2),
                "status": "pending_approval",
                "message": f"Attendance regularization request submitted for {reg_date}. Pending manager approval."
            }
            
        except ValueError as e:
            return {"success": False, "error": f"Invalid date/time format. {str(e)}"}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to request regularization: {str(e)}"}
    
    # ============================================================================
    # WORK ASSIGNMENT FUNCTION HANDLERS (NEW - Phase 4)
    # ============================================================================
    
    async def _handle_assign_work(self, args: Dict, user: User) -> Dict:
        """Assign work/task to an employee with AI validation"""
        try:
            # Get assigner (manager) employee record
            assigner = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not assigner:
                return {"success": False, "error": "Employee record not found"}
            
            # Check if user is a manager
            if not assigner.is_manager:
                return {
                    "success": False, 
                    "error": "Only managers can assign work to others. Use 'getMyTasks' to view your own tasks."
                }
            
            # Validate assignee exists and is active
            assignee = self.session.exec(
                select(Employee).where(Employee.id == args["assigneeId"])
            ).first()
            
            if not assignee:
                return {"success": False, "error": f"Employee with ID {args['assigneeId']} not found"}
            
            if not assignee.is_active:
                return {"success": False, "error": f"Employee {assignee.full_name} is not active"}
            
            # Check assignee's workload
            current_workload = assignee.current_workload_hours or 0
            max_workload = assignee.max_workload_hours or 40
            estimated_hours = args.get("estimatedHours", 0)
            
            if current_workload + estimated_hours > max_workload * 0.9:
                return {
                    "success": False,
                    "error": f"⚠️ {assignee.full_name} is near capacity ({current_workload}/{max_workload} hours). "
                           f"Adding {estimated_hours}h would overload them. Consider using 'suggestWorkAssignment' for alternatives."
                }
            
            # Parse due date if provided
            due_date = None
            if args.get("dueDate"):
                try:
                    due_date = datetime.strptime(args["dueDate"], "%Y-%m-%d").date()
                    if due_date < date.today():
                        return {"success": False, "error": "Due date cannot be in the past"}
                except ValueError:
                    return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
            
            # Create work assignment
            work_assignment = WorkAssignment(
                title=args["title"],
                description=args["description"],
                assigner_id=assigner.id,
                assignee_id=assignee.id,
                priority=TaskPriority(args["priority"]),
                status=TaskStatus.NOT_STARTED,
                due_date=due_date,
                estimated_hours=estimated_hours,
                project_name=args.get("projectName"),
                tags=args.get("tags", []),
                assigned_date=date.today()
            )
            
            self.session.add(work_assignment)
            self.session.commit()
            self.session.refresh(work_assignment)
            
            # Update assignee's workload
            assignee.current_workload_hours = current_workload + estimated_hours
            self.session.commit()
            
            # TODO: Send notification via NotificationService (will be added in Phase 6)
            
            return {
                "success": True,
                "task_id": work_assignment.id,
                "title": work_assignment.title,
                "assignee": assignee.full_name,
                "assignee_id": assignee.id,
                "priority": args["priority"],
                "due_date": str(due_date) if due_date else "Not set",
                "estimated_hours": estimated_hours,
                "new_workload": round(assignee.current_workload_hours, 1),
                "capacity_used": f"{round((assignee.current_workload_hours / max_workload) * 100)}%",
                "message": f"✅ Task '{args['title']}' assigned to {assignee.full_name}. They are now at {round((assignee.current_workload_hours / max_workload) * 100)}% capacity."
            }
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to assign work: {str(e)}"}
    
    async def _handle_get_my_tasks(self, args: Dict, user: User) -> Dict:
        """Get tasks assigned to current user with filters"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Build query
            query = select(WorkAssignment).where(WorkAssignment.assignee_id == employee.id)
            
            # Apply status filter
            status_filter = args.get("status", "all")
            if status_filter != "all":
                query = query.where(WorkAssignment.status == TaskStatus(status_filter))
            elif not args.get("includeCompleted", False):
                # By default, exclude completed tasks
                query = query.where(WorkAssignment.status != TaskStatus.COMPLETED)
            
            # Apply priority filter
            priority_filter = args.get("priority", "all")
            if priority_filter != "all":
                query = query.where(WorkAssignment.priority == TaskPriority(priority_filter))
            
            # Apply sorting
            sort_by = args.get("sortBy", "due_date")
            if sort_by == "due_date":
                query = query.order_by(WorkAssignment.due_date.asc())
            elif sort_by == "priority":
                # Custom priority order: urgent > high > medium > low
                priority_order = {
                    TaskPriority.URGENT: 4,
                    TaskPriority.HIGH: 3,
                    TaskPriority.MEDIUM: 2,
                    TaskPriority.LOW: 1
                }
                query = query.order_by(WorkAssignment.priority.desc())
            else:  # created_at
                query = query.order_by(WorkAssignment.created_at.desc())
            
            tasks = self.session.exec(query).all()
            
            # Format tasks
            task_list = []
            overdue_count = 0
            today = date.today()
            
            for task in tasks:
                is_overdue = task.due_date and task.due_date < today and task.status != TaskStatus.COMPLETED
                if is_overdue:
                    overdue_count += 1
                
                # Get assigner name
                assigner = self.session.get(Employee, task.assigner_id)
                
                days_until_due = None
                if task.due_date:
                    days_until_due = (task.due_date - today).days
                
                task_list.append({
                    "task_id": task.id,
                    "title": task.title,
                    "description": task.description[:100] + "..." if len(task.description or "") > 100 else task.description,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "progress": task.progress_percentage or 0,
                    "assigned_by": assigner.full_name if assigner else "Unknown",
                    "assigned_date": str(task.assigned_date),
                    "due_date": str(task.due_date) if task.due_date else "Not set",
                    "days_until_due": days_until_due,
                    "is_overdue": is_overdue,
                    "estimated_hours": task.estimated_hours,
                    "actual_hours": task.actual_hours or 0,
                    "project": task.project_name,
                    "tags": task.tags or []
                })
            
            # Calculate summary
            status_counts = {}
            for status in TaskStatus:
                count = sum(1 for t in tasks if t.status == status)
                if count > 0:
                    status_counts[status.value] = count
            
            priority_counts = {}
            for priority in TaskPriority:
                count = sum(1 for t in tasks if t.priority == priority)
                if count > 0:
                    priority_counts[priority.value] = count
            
            summary_msg = f"📋 You have {len(tasks)} task(s)"
            if overdue_count > 0:
                summary_msg += f" ({overdue_count} overdue)"
            
            return {
                "success": True,
                "tasks": task_list,
                "total_count": len(tasks),
                "overdue_count": overdue_count,
                "by_status": status_counts,
                "by_priority": priority_counts,
                "message": summary_msg
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get tasks: {str(e)}"}
    
    async def _handle_update_task_status(self, args: Dict, user: User) -> Dict:
        """Update task status and progress"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Get task
            task = self.session.get(WorkAssignment, args["taskId"])
            
            if not task:
                return {"success": False, "error": f"Task with ID {args['taskId']} not found"}
            
            # Check permission (assignee or assigner can update)
            if task.assignee_id != employee.id and task.assigner_id != employee.id:
                return {
                    "success": False,
                    "error": "You don't have permission to update this task. Only the assignee or assigner can update it."
                }
            
            old_status = task.status
            new_status = TaskStatus(args["status"])
            
            # Update status
            task.status = new_status
            
            # Update progress if provided
            if "progress" in args:
                task.progress_percentage = args["progress"]
            
            # Auto-set progress based on status
            if new_status == TaskStatus.NOT_STARTED and task.progress_percentage is None:
                task.progress_percentage = 0
            elif new_status == TaskStatus.COMPLETED and task.progress_percentage != 100:
                task.progress_percentage = 100
            
            # Add comment if provided
            if args.get("comment"):
                comment = TaskComment(
                    task_id=task.id,
                    employee_id=employee.id,
                    comment=args["comment"],
                    is_internal=False
                )
                self.session.add(comment)
            
            task.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(task)
            
            # TODO: Send notification to assigner if status changed (Phase 6)
            
            status_emoji = {
                "not_started": "⏸️",
                "in_progress": "🔄",
                "blocked": "🚫",
                "under_review": "👀",
                "completed": "✅",
                "cancelled": "❌"
            }
            
            return {
                "success": True,
                "task_id": task.id,
                "title": task.title,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "progress": task.progress_percentage,
                "emoji": status_emoji.get(new_status.value, "📝"),
                "message": f"{status_emoji.get(new_status.value, '📝')} Task '{task.title}' updated to {new_status.value.replace('_', ' ').title()} ({task.progress_percentage}%)"
            }
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to update task: {str(e)}"}
    
    async def _handle_get_team_workload(self, args: Dict, user: User) -> Dict:
        """Get team workload analysis (Manager only)"""
        try:
            manager = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not manager:
                return {"success": False, "error": "Employee record not found"}
            
            if not manager.is_manager:
                return {"success": False, "error": "Only managers can view team workload"}
            
            # Get team members reporting to this manager
            team_members = self.session.exec(
                select(Employee).where(
                    Employee.reporting_manager_id == manager.id,
                    Employee.is_active == True
                )
            ).all()
            
            if not team_members:
                return {
                    "success": True,
                    "team_workload": [],
                    "message": "No team members found reporting to you"
                }
            
            team_workload = []
            overloaded_count = 0
            available_count = 0
            
            for member in team_members:
                current_hours = member.current_workload_hours or 0
                max_hours = member.max_workload_hours or 40
                utilization = (current_hours / max_hours * 100) if max_hours > 0 else 0
                
                is_overloaded = utilization > 80
                is_available = utilization < 60
                
                if is_overloaded:
                    overloaded_count += 1
                if is_available:
                    available_count += 1
                
                # Apply filters
                if args.get("onlyOverloaded", False) and not is_overloaded:
                    continue
                if args.get("onlyAvailable", False) and not is_available:
                    continue
                
                member_data = {
                    "employee_id": member.id,
                    "name": member.full_name,
                    "email": member.email,
                    "current_workload_hours": round(current_hours, 1),
                    "max_workload_hours": max_hours,
                    "utilization_percent": round(utilization, 1),
                    "capacity_status": "overloaded" if is_overloaded else "available" if is_available else "balanced",
                    "available_hours": max(0, max_hours - current_hours),
                    "skills": member.skills or "Not specified"
                }
                
                # Include task details if requested
                if args.get("includeDetails", False):
                    active_tasks = self.session.exec(
                        select(WorkAssignment).where(
                            WorkAssignment.assignee_id == member.id,
                            WorkAssignment.status.in_([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED])
                        )
                    ).all()
                    
                    member_data["active_tasks"] = [
                        {
                            "task_id": task.id,
                            "title": task.title,
                            "priority": task.priority.value,
                            "status": task.status.value,
                            "due_date": str(task.due_date) if task.due_date else None,
                            "estimated_hours": task.estimated_hours
                        }
                        for task in active_tasks
                    ]
                    member_data["task_count"] = len(active_tasks)
                
                team_workload.append(member_data)
            
            # Sort by utilization descending
            team_workload.sort(key=lambda x: x["utilization_percent"], reverse=True)
            
            return {
                "success": True,
                "team_workload": team_workload,
                "team_size": len(team_members),
                "shown_count": len(team_workload),
                "overloaded_count": overloaded_count,
                "available_count": available_count,
                "message": f"📊 Team of {len(team_members)}: {overloaded_count} overloaded, {available_count} available"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get team workload: {str(e)}"}
    
    async def _handle_delegate_task(self, args: Dict, user: User) -> Dict:
        """Delegate task to another employee"""
        try:
            employee = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not employee:
                return {"success": False, "error": "Employee record not found"}
            
            # Get task
            task = self.session.get(WorkAssignment, args["taskId"])
            
            if not task:
                return {"success": False, "error": f"Task with ID {args['taskId']} not found"}
            
            # Check permission (current assignee or assigner can delegate)
            if task.assignee_id != employee.id and task.assigner_id != employee.id:
                return {"success": False, "error": "Only the current assignee or task owner can delegate this task"}
            
            # Validate new assignee
            new_assignee = self.session.get(Employee, args["newAssigneeId"])
            
            if not new_assignee:
                return {"success": False, "error": f"Employee with ID {args['newAssigneeId']} not found"}
            
            if not new_assignee.is_active:
                return {"success": False, "error": f"Employee {new_assignee.full_name} is not active"}
            
            if new_assignee.id == task.assignee_id:
                return {"success": False, "error": "Task is already assigned to this employee"}
            
            # Check new assignee's workload
            new_workload = new_assignee.current_workload_hours or 0
            max_workload = new_assignee.max_workload_hours or 40
            estimated_hours = task.estimated_hours or 0
            
            if new_workload + estimated_hours > max_workload * 0.9:
                return {
                    "success": False,
                    "error": f"⚠️ {new_assignee.full_name} is near capacity ({new_workload}/{max_workload} hours). Cannot delegate."
                }
            
            # Get old assignee for workload update
            old_assignee = self.session.get(Employee, task.assignee_id)
            old_assignee_name = old_assignee.full_name if old_assignee else "Previous assignee"
            
            # Update workloads
            if old_assignee and estimated_hours > 0:
                old_assignee.current_workload_hours = max(0, (old_assignee.current_workload_hours or 0) - estimated_hours)
            
            new_assignee.current_workload_hours = new_workload + estimated_hours
            
            # Update task
            task.assignee_id = new_assignee.id
            task.updated_at = datetime.utcnow()
            
            # Add delegation comment
            comment = TaskComment(
                task_id=task.id,
                employee_id=employee.id,
                comment=f"Task delegated from {old_assignee_name} to {new_assignee.full_name}. Reason: {args['reason']}",
                is_internal=False
            )
            self.session.add(comment)
            
            self.session.commit()
            
            # TODO: Send notifications (Phase 6)
            
            return {
                "success": True,
                "task_id": task.id,
                "title": task.title,
                "from_employee": old_assignee_name,
                "to_employee": new_assignee.full_name,
                "to_employee_id": new_assignee.id,
                "reason": args["reason"],
                "new_assignee_workload": round(new_assignee.current_workload_hours, 1),
                "new_assignee_capacity_used": f"{round((new_assignee.current_workload_hours / max_workload) * 100)}%",
                "message": f"✅ Task '{task.title}' delegated to {new_assignee.full_name}. They are now at {round((new_assignee.current_workload_hours / max_workload) * 100)}% capacity."
            }
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to delegate task: {str(e)}"}
    
    async def _handle_suggest_work_assignment(self, args: Dict, user: User) -> Dict:
        """AI-powered suggestions for task assignment based on skills and workload"""
        try:
            manager = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not manager:
                return {"success": False, "error": "Employee record not found"}
            
            if not manager.is_manager:
                return {"success": False, "error": "Only managers can get assignment suggestions"}
            
            # Get team members
            team_members = self.session.exec(
                select(Employee).where(
                    Employee.reporting_manager_id == manager.id,
                    Employee.is_active == True
                )
            ).all()
            
            if not team_members:
                return {"success": False, "error": "No team members found"}
            
            required_skills = args.get("requiredSkills", [])
            estimated_hours = args.get("estimatedHours", 0)
            priority = args.get("priority", "medium")
            top_n = args.get("topN", 3)
            
            # Score each team member
            suggestions = []
            for member in team_members:
                score = 0
                reasons = []
                
                # Skill matching (40% weight)
                member_skills = (member.skills or "").lower().split(",")
                member_skills = [s.strip() for s in member_skills if s.strip()]
                
                if required_skills:
                    skill_matches = sum(1 for skill in required_skills if skill.lower() in " ".join(member_skills))
                    skill_score = (skill_matches / len(required_skills)) * 40 if len(required_skills) > 0 else 20
                    score += skill_score
                    
                    if skill_matches > 0:
                        reasons.append(f"Matches {skill_matches}/{len(required_skills)} required skills")
                else:
                    score += 20  # Neutral score if no skills specified
                
                # Workload availability (40% weight)
                current_workload = member.current_workload_hours or 0
                max_workload = member.max_workload_hours or 40
                utilization = (current_workload / max_workload) if max_workload > 0 else 0
                
                if current_workload + estimated_hours <= max_workload * 0.8:
                    # Under 80% capacity after assignment - good
                    workload_score = (1 - utilization) * 40
                    score += workload_score
                    reasons.append(f"Has capacity ({round(utilization * 100)}% utilized)")
                elif current_workload + estimated_hours <= max_workload:
                    # 80-100% capacity - acceptable
                    workload_score = (1 - utilization) * 20
                    score += workload_score
                    reasons.append(f"Near capacity ({round(utilization * 100)}% utilized)")
                else:
                    # Over capacity - penalize
                    reasons.append(f"⚠️ Would be overloaded ({round(utilization * 100)}% utilized)")
                
                # Priority handling experience (20% weight)
                # Check recent tasks with same priority
                recent_high_priority = self.session.exec(
                    select(WorkAssignment).where(
                        WorkAssignment.assignee_id == member.id,
                        WorkAssignment.priority == TaskPriority(priority),
                        WorkAssignment.status == TaskStatus.COMPLETED
                    ).limit(5)
                ).all()
                
                if len(recent_high_priority) > 0:
                    experience_score = min(len(recent_high_priority) * 4, 20)
                    score += experience_score
                    reasons.append(f"Completed {len(recent_high_priority)} {priority} priority tasks")
                
                suggestions.append({
                    "employee_id": member.id,
                    "name": member.full_name,
                    "email": member.email,
                    "score": round(score, 1),
                    "current_workload_hours": round(current_workload, 1),
                    "max_workload_hours": max_workload,
                    "utilization_percent": round(utilization * 100, 1),
                    "available_hours": round(max(0, max_workload - current_workload), 1),
                    "skills": member.skills or "Not specified",
                    "reasons": reasons,
                    "recommendation": "Highly Recommended" if score >= 70 else "Recommended" if score >= 50 else "Consider"
                })
            
            # Sort by score descending
            suggestions.sort(key=lambda x: x["score"], reverse=True)
            
            # Return top N
            top_suggestions = suggestions[:top_n]
            
            if not top_suggestions:
                return {"success": False, "error": "No suitable team members found"}
            
            return {
                "success": True,
                "suggestions": top_suggestions,
                "task_description": args["taskDescription"],
                "required_skills": required_skills,
                "estimated_hours": estimated_hours,
                "priority": priority,
                "message": f"🤖 Found {len(top_suggestions)} suggestion(s) based on skills, workload, and experience"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get suggestions: {str(e)}"}

    async def _handle_send_broadcast_message(self, args: Dict, user: User) -> Dict:
        """Send broadcast message to recipients through notification system"""
        try:
            from app.models.extras import Notification
            
            message = args["message"]
            recipient_type = args["recipientType"]
            recipient_ids = args.get("recipientIds", [])
            scheduled_time = args.get("scheduledTime")
            priority = args.get("priority", "medium")
            template_used = args.get("templateUsed")
            
            # Get sender employee
            sender = self.session.exec(
                select(Employee).where(Employee.user_id == user.id)
            ).first()
            
            if not sender:
                return {"success": False, "error": "Sender employee record not found"}
            
            # Determine recipients based on type
            recipients = []
            
            if recipient_type == "all_employees":
                # All active employees
                recipients = self.session.exec(
                    select(Employee).where(Employee.is_active == True)
                ).all()
                recipient_description = "all employees"
                
            elif recipient_type == "all_managers":
                # All managers
                recipients = self.session.exec(
                    select(Employee).where(
                        Employee.is_active == True,
                        Employee.is_manager == True
                    )
                ).all()
                recipient_description = "all managers"
                
            elif recipient_type == "specific_teams":
                # Employees in specific teams
                if not recipient_ids:
                    return {"success": False, "error": "Team IDs required for specific_teams recipient type"}
                
                recipients = self.session.exec(
                    select(Employee).where(
                        Employee.is_active == True,
                        Employee.team_id.in_(recipient_ids)
                    )
                ).all()
                recipient_description = f"{len(recipient_ids)} team(s)"
                
            elif recipient_type == "custom":
                # Specific employees
                if not recipient_ids:
                    return {"success": False, "error": "Employee IDs required for custom recipient type"}
                
                recipients = self.session.exec(
                    select(Employee).where(
                        Employee.is_active == True,
                        Employee.id.in_(recipient_ids)
                    )
                ).all()
                recipient_description = f"{len(recipient_ids)} selected recipient(s)"
            else:
                return {"success": False, "error": f"Invalid recipient type: {recipient_type}"}
            
            if not recipients:
                return {"success": False, "error": f"No recipients found for {recipient_description}"}
            
            # If scheduled, store for later processing
            if scheduled_time:
                # TODO: Store in scheduled_broadcasts table
                return {
                    "success": True,
                    "scheduled": True,
                    "scheduled_time": scheduled_time,
                    "recipient_count": len(recipients),
                    "recipient_description": recipient_description,
                    "message": f"📅 Broadcast scheduled for {scheduled_time} to {len(recipients)} recipient(s)"
                }
            
            # Send immediately via notification system
            notifications_created = 0
            for recipient in recipients:
                # Skip sender
                if recipient.id == sender.id:
                    continue
                
                notification = Notification(
                    employee_id=recipient.id,
                    title=f"📢 Broadcast from {sender.full_name}",
                    message=message,
                    notification_type="broadcast",
                    priority=priority,
                    metadata=json.dumps({
                        "sender_id": sender.id,
                        "sender_name": sender.full_name,
                        "recipient_type": recipient_type,
                        "template_used": template_used,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                self.session.add(notification)
                notifications_created += 1
            
            self.session.commit()
            
            return {
                "success": True,
                "notifications_sent": notifications_created,
                "recipient_count": len(recipients),
                "recipient_description": recipient_description,
                "recipient_type": recipient_type,
                "priority": priority,
                "template_used": template_used,
                "message": f"✅ Broadcast sent to {notifications_created} recipient(s) ({recipient_description})",
                "details": {
                    "sender": sender.full_name,
                    "message_preview": message[:100] + ("..." if len(message) > 100 else ""),
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": f"Failed to send broadcast: {str(e)}"}

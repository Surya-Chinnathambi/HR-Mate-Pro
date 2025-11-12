# HRMS Portal - Role-Based Access & Chat History Implementation Guide

## Overview
This document outlines the implementation of:
1. Role-based dashboards (Employee, Manager, HR)
2. Rename "Inbox" to "WorkInbox" throughout the application
3. Chat history persistence (like ChatGPT)
4. Team privacy structure (2 HR, 6 Managers, 30 Employees)

## Database Changes Required

### 1. Run Migration for Chat Tables
```bash
cd hrms_backend
alembic upgrade head
```

This creates:
- `chat_conversations` table (conversation metadata)
- `chat_messages` table (individual messages)
- Adds `team_id` and `role` columns to `employees` table

### 2. Update Employee Records with Roles
```sql
-- Set HR roles (2 employees)
UPDATE employees SET role = 'hr' WHERE id IN (1, 2);

-- Set Manager roles (6 employees)  
UPDATE employees SET role = 'manager', is_manager = true WHERE id IN (3, 4, 5, 6, 7, 8);

-- Remaining 30 are employees (default role = 'employee')

-- Assign team_id to create 6 teams
UPDATE employees SET team_id = 1 WHERE manager_id = 3;  -- Team 1 under Manager 3
UPDATE employees SET team_id = 2 WHERE manager_id = 4;  -- Team 2 under Manager 4
-- ... continue for all 6 managers
```

## Backend API Changes

### 1. Register Chat API Router
**File**: `hrms_backend/app/main.py`

```python
from app.api import chat

# Add to router registration
app.include_router(chat.router)
```

### 2. Add Team Isolation Middleware
**File**: `hrms_backend/app/api/employees.py`

Add team filtering to all employee queries:

```python
def get_team_filtered_employees(session: Session, current_employee: Employee):
    """
    Filter employees based on role:
    - HR: See all employees
    - Manager: See only their team
    - Employee: See only themselves
    """
    if current_employee.role == 'hr':
        # HR sees everyone
        return select(Employee).where(Employee.is_active == True)
    elif current_employee.role == 'manager':
        # Manager sees their team
        return select(Employee).where(
            or_(
                Employee.team_id == current_employee.team_id,
                Employee.id == current_employee.id
            )
        )
    else:
        # Employee sees only themselves
        return select(Employee).where(Employee.id == current_employee.id)
```

### 3. Update All Relevant API Endpoints
Apply team filtering to:
- `/api/employees/all/list` - Filter by team
- `/api/attendance/*` - Show only team attendance for managers
- `/api/workflow/*` - Task assignments within team only
- `/api/approvals/*` - Managers approve only their team's requests
- `/api/analytics/*` - Metrics scoped to team

## Frontend Changes

### 1. Role-Based Dashboard Routing
**File**: `src/components/EnhancedHRMSDashboard.tsx`

```typescript
// Add at component initialization
const [userRole, setUserRole] = useState<'employee' | 'manager' | 'hr'>('employee');

useEffect(() => {
  // Fetch employee role
  const fetchRole = async () => {
    const empRes = await apiClient.get('/employees/current');
    setUserRole(empRes.data.role || 'employee');
  };
  fetchRole();
}, []);

// Render appropriate dashboard
const renderDashboard = () => {
  switch (userRole) {
    case 'hr':
      return <HRDashboard />;
    case 'manager':
      return <ManagerDashboard />;
    default:
      return <EmployeeDashboard />;
  }
};
```

### 2. Rename Inbox → WorkInbox

**Files to Update**:
1. `src/components/EnhancedHRMSDashboard.tsx` - Change menu labels
2. `src/components/NotificationInbox.tsx` → Rename to `NotificationCenter.tsx`
3. Update all imports and references

**Search & Replace**:
```bash
# In frontend
Find: "Inbox" (component name)
Replace with: "NotificationCenter"

Find: "inbox" (route/id)
Replace with: "notifications"

# Keep "WorkInbox" as is - already correct
```

### 3. Chat History Sidebar
**New File**: `src/components/ChatHistorySidebar.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { Plus, Archive, Pin, Trash2, Edit2 } from 'lucide-react';

interface Conversation {
  id: number;
  title: string;
  is_pinned: boolean;
  is_active: boolean;
  last_message_at: string;
  message_count: number;
}

export function ChatHistorySidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    const res = await apiClient.get('/api/chat/conversations');
    setConversations(res.data.conversations);
    const active = res.data.conversations.find((c: Conversation) => c.is_active);
    if (active) setActiveConversationId(active.id);
  };

  const createNewChat = async () => {
    const res = await apiClient.post('/api/chat/conversations');
    setActiveConversationId(res.data.id);
    loadConversations();
  };

  const switchConversation = async (conversationId: number) => {
    await apiClient.put(`/api/chat/conversations/${conversationId}/activate`);
    setActiveConversationId(conversationId);
  };

  const deleteConversation = async (conversationId: number) => {
    if (confirm('Delete this conversation?')) {
      await apiClient.delete(`/api/chat/conversations/${conversationId}`);
      loadConversations();
    }
  };

  return (
    <div className="w-64 bg-gray-900 text-white h-full flex flex-col">
      {/* New Chat Button */}
      <button
        onClick={createNewChat}
        className="m-4 p-3 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center justify-center gap-2"
      >
        <Plus size={20} />
        <span>New Chat</span>
      </button>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            onClick={() => switchConversation(conv.id)}
            className={`p-3 mx-2 my-1 rounded-lg cursor-pointer flex items-center justify-between group ${
              activeConversationId === conv.id
                ? 'bg-gray-700'
                : 'hover:bg-gray-800'
            }`}
          >
            <div className="flex-1 truncate">
              <div className="flex items-center gap-2">
                {conv.is_pinned && <Pin size={14} className="text-yellow-400" />}
                <span className="text-sm truncate">{conv.title}</span>
              </div>
              <span className="text-xs text-gray-400">
                {conv.message_count} messages
              </span>
            </div>
            
            {/* Actions */}
            <div className="hidden group-hover:flex gap-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                className="p-1 hover:bg-red-600 rounded"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 4. Update AI Command Center
**File**: `src/components/AICommandCenter.tsx`

Add chat history sidebar and integrate with conversation APIs:

```typescript
// Add state
const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
const [showHistory, setShowHistory] = useState(true);

// Load active conversation on mount
useEffect(() => {
  loadActiveConversation();
}, []);

const loadActiveConversation = async () => {
  const res = await apiClient.get('/api/chat/active');
  setCurrentConversationId(res.data.conversation.id);
  setMessages(res.data.messages);
};

// Save messages to database
const saveMessage = async (role: 'USER' | 'ASSISTANT', content: string) => {
  if (!currentConversationId) return;
  
  await apiClient.post(`/api/chat/conversations/${currentConversationId}/messages`, {
    role,
    content
  });
};

// Render with sidebar
return (
  <div className="flex h-full">
    {showHistory && <ChatHistorySidebar />}
    <div className="flex-1">
      {/* Existing chat UI */}
    </div>
  </div>
);
```

## Team Privacy Implementation

### Query Modifications Required

**1. Attendance Queries**
```python
# Before
attendance = session.exec(select(AttendanceDay)).all()

# After
attendance = session.exec(
    select(AttendanceDay)
    .join(Employee)
    .where(Employee.team_id == current_employee.team_id)  # If manager
).all()
```

**2. Leave Approvals**
```python
# Before
leaves = session.exec(select(LeaveApplication)).all()

# After
if current_employee.role == 'manager':
    # Only show leaves from team members
    leaves = session.exec(
        select(LeaveApplication)
        .join(Employee)
        .where(Employee.team_id == current_employee.team_id)
    ).all()
```

**3. Work Assignments**
```python
# Managers can only assign tasks to their team
if current_employee.role == 'manager':
    assignable_employees = session.exec(
        select(Employee).where(Employee.team_id == current_employee.team_id)
    ).all()
```

## Testing Checklist

### Backend Tests
- [ ] Chat conversation CRUD operations
- [ ] Message persistence and retrieval
- [ ] Team isolation in employee queries
- [ ] Role-based API access control
- [ ] Manager can only see their team
- [ ] HR can see all employees

### Frontend Tests
- [ ] Different dashboard renders for each role
- [ ] Chat history sidebar shows all conversations
- [ ] New chat creation and switching
- [ ] Conversation deletion
- [ ] WorkInbox naming (no more generic "Inbox")
- [ ] Team members visible only to their manager

## Deployment Steps

1. **Backup Database**
   ```bash
   pg_dump hrms_db > backup_before_chat_history.sql
   ```

2. **Run Migration**
   ```bash
   cd hrms_backend
   alembic upgrade head
   ```

3. **Update Employee Roles**
   Run SQL script to set roles and team_ids

4. **Deploy Backend**
   ```bash
   # Restart backend with new endpoints
   uvicorn app.main:app --reload --port 8000
   ```

5. **Deploy Frontend**
   ```bash
   npm run build
   # Deploy dist folder
   ```

## Summary of Changes

### Database
- ✅ New tables: `chat_conversations`, `chat_messages`
- ✅ New columns: `employees.role`, `employees.team_id`
- ✅ Indexes for performance

### Backend (Python/FastAPI)
- ✅ New file: `app/api/chat.py` (20+ endpoints)
- ✅ New file: `app/models/chat.py` (Chat models)
- ✅ Updated: All API endpoints with team filtering
- ✅ Migration: `alembic/versions/006_chat_history.py`

### Frontend (React/TypeScript)
- ✅ New component: `ChatHistorySidebar.tsx`
- ✅ Updated: `AICommandCenter.tsx` (chat persistence)
- ✅ Updated: `EnhancedHRMSDashboard.tsx` (role-based routing)
- ✅ Renamed: "Inbox" → "NotificationCenter", keep "WorkInbox"
- ✅ New dashboards: `HRDashboard.tsx`, `ManagerDashboard.tsx` (enhanced)

## File Locations

All new/modified files are in:
- `hrms_backend/app/api/chat.py`
- `hrms_backend/app/models/chat.py`
- `hrms_backend/alembic/versions/006_chat_history.py`
- `src/components/ChatHistorySidebar.tsx`
- `src/components/AICommandCenter.tsx` (updated)
- `src/components/EnhancedHRMSDashboard.tsx` (updated)

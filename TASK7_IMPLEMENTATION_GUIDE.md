# Task 7: Frontend UI Integration - Implementation Guide

## Completed Components ✅

### 1. Real-time Infrastructure
- **useWebSocket.ts**: Native WebSocket hook with auto-reconnection, heartbeat
- **useNotifications.ts**: Notification management with real-time updates
- **NotificationBell.tsx**: Dropdown notification bell with unread count
- **EnhancedHomeDashboard.tsx**: Real-time home dashboard with live stats

### 2. API Client Enhancement
- Comprehensive endpoint organization by module
- All backend endpoints integrated:
  - Auth, Inbox, Messages, Broadcasts
  - Team (manager analytics)
  - Employees, Attendance, Leaves, Tasks
  - Expenses, Performance, Payroll
  - Analytics, Policies, Helpdesk

## Implementation Status

### Phase 1: Core Infrastructure ✅ COMPLETE
- [x] Enhanced API client with all endpoints
- [x] WebSocket hook (native WebSocket, not Socket.IO)
- [x] Notifications hook with real-time updates
- [x] Notification bell component
- [x] Enhanced home dashboard

### Phase 2: Core Modules 🚧 IN PROGRESS
- [ ] **Work Inbox**: Full-featured inbox with filters, real-time updates
- [ ] **Messages**: Direct messaging with real-time chat
- [ ] **Broadcasts**: Create/view company-wide announcements
- [ ] **Attendance**: Real-time check-in/out with live status
- [ ] **Leave**: Apply/approve leaves with instant notifications

### Phase 3: Manager & Analytics Modules 📋 PENDING
- [ ] **My Team**: Live workload distribution, attendance tracking
- [ ] **Team Analytics**: Real-time charts for team performance
- [ ] **Analytics Dashboard**: Company-wide metrics with live data

### Phase 4: Additional Modules 📋 PENDING
- [ ] **Performance**: Reviews and feedback system
- [ ] **Expenses & Travel**: Expense claims with approval workflow
- [ ] **Helpdesk**: Ticket management system
- [ ] **Org Directory**: Employee directory with live status
- [ ] **Engage**: Employee engagement features
- [ ] **Company Policies**: Policy management and acknowledgment

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Application                     │
├─────────────────────────────────────────────────────────────┤
│  Components                                                  │
│  ├── NotificationBell (real-time unread count)             │
│  ├── EnhancedHomeDashboard (live stats)                    │
│  ├── WorkInbox (real-time inbox)                           │
│  └── ... (other modules)                                    │
├─────────────────────────────────────────────────────────────┤
│  Hooks                                                       │
│  ├── useWebSocket (native WebSocket connection)            │
│  ├── useNotifications (notification CRUD + real-time)      │
│  └── ... (module-specific hooks)                           │
├─────────────────────────────────────────────────────────────┤
│  API Client                                                  │
│  └── api.* (organized endpoints for all modules)           │
└─────────────────────────────────────────────────────────────┘
                              ↕
                    WebSocket Connection
                 (ws://localhost:8000/ws?token=JWT)
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      Backend Services                        │
├─────────────────────────────────────────────────────────────┤
│  WebSocket Manager (connection tracking, JWT auth)          │
├─────────────────────────────────────────────────────────────┤
│  Workers                                                     │
│  ├── PostgreSQL Listener (pg_notify → Redis)               │
│  ├── Notification Workers (email/slack/push)               │
│  └── WebSocket Broadcaster (Redis → connected clients)     │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Endpoints                                           │
│  └── /inbox, /messages, /broadcasts, /team, etc.           │
└─────────────────────────────────────────────────────────────┘
```

## WebSocket Event Types

### Incoming Events (Backend → Frontend)
- `new_notification`: New notification created
- `notification_updated`: Notification marked as read
- `notification_deleted`: Notification removed
- `task_assigned`: New task assigned to user
- `task_updated`: Task status or details changed
- `leave_approved`: Leave request approved
- `leave_rejected`: Leave request rejected
- `message_received`: New direct message
- `broadcast_received`: Company-wide broadcast
- `attendance_checked_in`: User checked in
- `attendance_checked_out`: User checked out
- `expense_approved`: Expense claim approved
- `expense_rejected`: Expense claim rejected

### Outgoing Events (Frontend → Backend)
- `ping`: Heartbeat to keep connection alive
- (Future: chat messages, typing indicators, etc.)

## Usage Examples

### 1. Using Notifications Hook

```typescript
import { useNotifications } from '../hooks/useNotifications';

function MyComponent() {
  const {
    notifications,
    unreadCount,
    loading,
    isConnected,
    markAsRead,
    markAllAsRead,
    deleteNotification,
  } = useNotifications();

  return (
    <div>
      <h1>Notifications ({unreadCount})</h1>
      {notifications.map(notif => (
        <div key={notif.id}>
          <h3>{notif.title}</h3>
          <p>{notif.body}</p>
          {!notif.is_read && (
            <button onClick={() => markAsRead(notif.id)}>
              Mark as read
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 2. Using WebSocket Directly

```typescript
import { useWebSocket } from '../hooks/useWebSocket';

function MyComponent() {
  const { status, isConnected, lastMessage, sendMessage } = useWebSocket({
    autoConnect: true,
    onMessage: (message) => {
      console.log('Received:', message);
      
      if (message.type === 'task_assigned') {
        // Handle new task
        toast.success(`New task: ${message.data.title}`);
      }
    },
  });

  return (
    <div>
      <span>Status: {status}</span>
      {isConnected && <span>🟢 Connected</span>}
    </div>
  );
}
```

### 3. Making API Calls

```typescript
import { api } from '../api/client';

async function loadData() {
  // Get notifications
  const notifs = await api.inbox.getNotifications({ limit: 50 });
  
  // Send message
  await api.messages.send({
    recipient_employee_id: 123,
    subject: 'Hello',
    body: 'Message content',
  });
  
  // Get team workload
  const workload = await api.team.getWorkload();
  
  // Mark attendance
  await api.attendance.checkIn({ location: 'Office' });
}
```

## Next Steps

### Immediate (Phase 2)
1. Create EnhancedWorkInbox component with:
   - Real-time notification feed
   - Filtering by type, read/unread
   - Bulk actions (mark all read, delete)
   - Auto-refresh on WebSocket events

2. Create MessagingModule with:
   - Direct messaging UI
   - Real-time message delivery
   - Read receipts
   - Message composition

3. Create BroadcastsModule with:
   - View broadcasts
   - Create broadcasts (HR/Manager)
   - Target scope selection
   - Real-time delivery confirmation

### Short-term (Phase 3)
4. Enhanced MyTeamModule with:
   - Live team workload charts
   - Real-time attendance tracking
   - Pending leave approvals
   - Performance summary

5. Analytics Dashboard with:
   - Live charts and metrics
   - Attendance analytics
   - Leave analytics
   - Workload distribution

### Medium-term (Phase 4)
6. Complete remaining modules
7. Implement toast notification system
8. Add loading states and error handling
9. Optimize performance (memoization, lazy loading)
10. Add e2e tests

## Environment Variables

```env
# Frontend (.env)
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws

# Backend (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/hrms
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
```

## Running the Full Stack

### Backend
```bash
cd hrms_backend

# Start workers (in one terminal)
python run_workers.py

# Start FastAPI (in another terminal)
uvicorn app.main:app --reload
```

### Frontend
```bash
# Install dependencies
npm install react-hot-toast date-fns lucide-react

# Start dev server
npm run dev
```

## Testing Real-time Features

1. **Open two browser windows** (different users)
2. **Login as Manager** in window 1
3. **Login as Employee** in window 2
4. **Assign task from Manager → Employee**
5. **Verify real-time notification** appears in Employee window
6. **Check WebSocket status** (green dot) in both windows
7. **Test other features**: messages, broadcasts, leave approvals

## Troubleshooting

### WebSocket not connecting
- Check VITE_WS_URL is correct
- Verify JWT token in localStorage
- Check backend workers are running
- Check CORS settings in backend

### Notifications not appearing
- Verify worker orchestrator is running
- Check Redis is running
- Check PostgreSQL NOTIFY triggers exist
- Check WebSocket connection status

### API calls failing
- Verify VITE_API_URL is correct
- Check JWT token in Authorization header
- Verify backend endpoints exist
- Check network tab for error details

## Performance Optimizations

1. **Lazy load modules** - Use React.lazy() for large components
2. **Memoize expensive computations** - Use useMemo/useCallback
3. **Virtual scrolling** - For long notification/message lists
4. **Debounce searches** - Avoid excessive API calls
5. **WebSocket reconnection backoff** - Exponential delay
6. **Pagination** - Load data in chunks
7. **Caching** - Store frequently accessed data

## Security Considerations

1. **JWT validation** - WebSocket validates token on connection
2. **RBAC** - Backend enforces permissions on all endpoints
3. **Input sanitization** - Validate all user inputs
4. **XSS protection** - Escape HTML in messages/notifications
5. **Rate limiting** - Backend rate limits API calls
6. **Audit logging** - All actions logged in audit_logs table

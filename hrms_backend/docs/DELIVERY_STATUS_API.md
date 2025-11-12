# Delivery Status API Documentation

## Overview

All automation service write operations now return a detailed `delivery_status` object that provides visibility into the 4-step execution pattern:

1. **Entity Created** - Primary entity (task, leave, attendance, etc.) was created
2. **Inbox Notification Created** - Recipients were notified via inbox_notifications table
3. **Event Emitted** - PostgreSQL pg_notify event was triggered for downstream processing
4. **Audit Logged** - Action was recorded in audit_logs table

## API Response Format

When calling automation services through the AI chat endpoint (`/api/ai/chat`), the response includes:

```json
{
  "response": "AI-generated text response",
  "intent": "detected_intent",
  "conversation_id": "uuid",
  "automated_action": {
    "success": true,
    "message": "Operation completed successfully",
    "entity_id": 123,
    "delivery_status": {
      "entity_created": true,
      "inbox_notification_created": true,
      "event_emitted": true,
      "audit_logged": true,
      "event_channel": "tasks_events",
      "inbox_ids": [456, 789],
      "error": null
    }
  }
}
```

## Services with Delivery Status

### 1. TaskAutomationService.assign_task

**Endpoint**: Called via AI chat or `/api/work-assignments/assign`

**Delivery Status Fields**:
```json
{
  "task_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "tasks_events",
  "audit_logged": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Assignee receives task assignment notification
- Assigner receives confirmation notification

---

### 2. LeaveAutomationService.submit_leave_application

**Endpoint**: Called via AI chat or `/api/leaves/apply`

**Delivery Status Fields**:
```json
{
  "leave_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "leave_requests_events",
  "audit_logged": true,
  "manager_notified": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Employee receives leave application confirmation
- Manager receives leave approval request

---

### 3. AttendanceAutomationService.clock_in

**Endpoint**: Called via AI chat when user says "clock in"

**Delivery Status Fields**:
```json
{
  "entity_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "attendance_events",
  "audit_logged": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Employee receives clock-in confirmation
- Manager receives late arrival alert (if 3+ late arrivals this month)

---

### 4. AttendanceAutomationService.clock_out

**Endpoint**: Called via AI chat when user says "clock out"

**Delivery Status Fields**:
```json
{
  "entity_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "attendance_events",
  "audit_logged": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Employee receives clock-out confirmation with work hours summary

---

### 5. WFHAutomationService.submit_wfh_request

**Endpoint**: Called via AI chat or `/api/wfh/request`

**Delivery Status Fields**:
```json
{
  "entity_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "wfh_request_events",
  "audit_logged": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Employee receives WFH request confirmation
- Manager receives WFH approval request

---

### 6. ExpenseAutomationService.submit_expense_claim

**Endpoint**: Called via AI chat or `/api/expenses/submit`

**Delivery Status Fields**:
```json
{
  "entity_created": true,
  "inbox_notification_created": true,
  "event_emitted": true,
  "event_channel": "expense_claim_events",
  "audit_logged": true,
  "inbox_ids": [notifications_created],
  "error": null
}
```

**Notifications Created**:
- Employee receives expense claim confirmation
- Manager receives expense approval request

---

## Error Handling

When an operation fails, the delivery_status reflects partial completion:

```json
{
  "success": false,
  "error": "operation_failed",
  "message": "Failed to complete operation: <reason>",
  "delivery_status": {
    "entity_created": false,
    "inbox_notification_created": false,
    "event_emitted": false,
    "audit_logged": false,
    "event_channel": null,
    "inbox_ids": [],
    "error": "Database transaction rolled back due to constraint violation"
  }
}
```

All operations use database transactions with automatic rollback on failure, ensuring data consistency.

## Using Delivery Status

### Frontend Integration

```typescript
// Example: Handle clock-in response
const handleClockIn = async () => {
  const response = await fetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'clock in' })
  });
  
  const data = await response.json();
  
  if (data.automated_action?.delivery_status) {
    const status = data.automated_action.delivery_status;
    
    // Check if notification was created
    if (status.inbox_notification_created) {
      console.log(`Created ${status.inbox_ids.length} notifications`);
      // Trigger notification badge update
      updateNotificationBadge();
    }
    
    // Check if event was emitted for real-time updates
    if (status.event_emitted) {
      console.log(`Event emitted on channel: ${status.event_channel}`);
      // WebSocket listener will receive this event
    }
    
    // Check audit trail
    if (status.audit_logged) {
      console.log('Action logged for compliance');
    }
  }
};
```

### Monitoring & Debugging

The delivery_status enables:
- **Observability**: Track which steps succeeded/failed
- **Debugging**: Identify bottlenecks in the 4-step pattern
- **Audit Compliance**: Verify all actions are logged
- **Real-time Sync**: Confirm events are emitted for WebSocket delivery

## Next Steps

1. **Notification Engine**: Build Redis/Bull workers to process `event_channel` events
2. **WebSocket Server**: Implement real-time delivery based on emitted events
3. **Monitoring Dashboard**: Create admin view showing delivery_status metrics
4. **Retry Logic**: Add automatic retry for failed notification deliveries

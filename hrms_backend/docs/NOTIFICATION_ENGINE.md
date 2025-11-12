# Notification Engine Documentation

## Architecture Overview

The notification engine implements a complete event-driven architecture for real-time notifications across the HRMS platform.

```
┌─────────────────┐
│   FastAPI App   │
│  (Write Events) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   PostgreSQL    │──────▶│  PL/pgSQL        │
│   Tables        │      │  Triggers        │
│  - tasks        │      │  - emit_task     │
│  - leaves       │      │  - emit_leave    │
│  - messages     │      │  - emit_message  │
│  - inbox_notif  │      │  - emit_inbox    │
└─────────────────┘      └────────┬─────────┘
                                  │ pg_notify
                                  ▼
                         ┌──────────────────┐
                         │  Postgres        │
                         │  Event Listener  │
                         │  (Python Worker) │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  Redis Pub/Sub   │
                         │  & Queues        │
                         └─────┬──────┬─────┘
                               │      │
                   ┌───────────┘      └────────────┐
                   ▼                                ▼
          ┌────────────────┐             ┌─────────────────┐
          │  Notification  │             │   WebSocket     │
          │  Workers       │             │   Broadcaster   │
          │  - Email       │             └────────┬────────┘
          │  - Slack       │                      │
          │  - Push        │                      ▼
          └────────────────┘             ┌─────────────────┐
                                         │  Connected      │
                                         │  WebSocket      │
                                         │  Clients        │
                                         └─────────────────┘
```

## Components

### 1. Database Triggers (PostgreSQL)

**Location**: `hrms_backend/db/migrations/0001_create_notifications_schema.sql`

PL/pgSQL triggers automatically emit `NOTIFY` events when records are inserted:

- **`trg_emit_task_event`** - Fires on `tasks` table inserts
- **`trg_emit_leave_event`** - Fires on `leave_requests` table inserts
- **`trg_emit_message_event`** - Fires on `messages` table inserts
- **`trg_emit_inbox_event`** - Fires on `inbox_notifications` table inserts

### 2. PostgreSQL Event Listener

**Location**: `hrms_backend/app/workers/postgres_listener.py`

**Purpose**: Bridges PostgreSQL NOTIFY to Redis pub/sub

**Features**:
- Listens to 7 PostgreSQL channels
- Forwards events to Redis for distributed processing
- Routes events to appropriate worker queues
- Determines priority based on event type

**Channels**:
```python
tasks_events
leave_requests_events
messages_events
inbox_events
attendance_events
wfh_request_events
expense_claim_events
```

### 3. Redis Infrastructure

**Location**: `hrms_backend/app/core/redis_client.py`

**Pub/Sub Channels**:
- Mirror PostgreSQL NOTIFY channels
- User-specific channels: `user:{user_id}:events`

**Job Queues** (Priority queues using sorted sets):
- `queue:email` - Email notifications
- `queue:slack` - Slack messages
- `queue:push` - Push notifications
- `queue:websocket` - WebSocket broadcasts

**Connection Tracking**:
- `ws:connections` - Hash of all WebSocket connections
- `ws:user:{user_id}` - User's connection data

### 4. Notification Workers

**Location**: `hrms_backend/app/workers/notification_worker.py`

**Purpose**: Process notification jobs from Redis queues

**Features**:
- Consumes jobs from email/Slack/push queues
- Implements retry logic with exponential backoff
- Updates `inbox_notifications.delivery_channel` after successful delivery
- Supports multiple worker instances for scalability

**Retry Configuration**:
```python
max_retries = 3
retry_delays = [5, 30, 300]  # 5s, 30s, 5min
```

### 5. WebSocket Manager

**Location**: `hrms_backend/app/core/websocket_manager.py`

**Purpose**: Manage WebSocket connections and real-time broadcasting

**Features**:
- JWT authentication for WebSocket connections
- Connection tracking in Redis (distributed support)
- Send to specific users or broadcast to all
- Heartbeat/ping-pong for connection health
- Automatic cleanup of dead connections

**API**:
```python
# Connect user
await manager.connect(websocket, user_id, connection_id)

# Send to specific user
await manager.send_personal_message(message, user_id)

# Broadcast to all
await manager.broadcast(message)

# Disconnect
await manager.disconnect(connection_id, user_id)
```

### 6. WebSocket Endpoint

**Location**: `hrms_backend/app/api/websocket.py`

**Endpoint**: `ws://localhost:8000/api/ws/notifications?token=<jwt>`

**Message Types Sent**:
- `connection` - Connection established
- `notification` - New notification
- `task_assigned` - Task assignment
- `leave_approved` - Leave approval
- `message_received` - New message
- `ping` - Heartbeat
- `error` - Error message

**Message Types Received**:
- `auth` - Authentication (if token not in query)
- `pong` - Heartbeat response
- `subscribe` - Subscribe to channels
- `unsubscribe` - Unsubscribe from channels
- `mark_read` - Mark notification as read

### 7. Worker Orchestrator

**Location**: `hrms_backend/run_workers.py`

**Purpose**: Run all workers as a single service

**Workers Started**:
1. PostgreSQL Event Listener
2. Notification Worker #1
3. Notification Worker #2
4. WebSocket Broadcaster

**Usage**:
```bash
cd hrms_backend
python run_workers.py
```

## Event Flow

### Example: Task Assignment

1. **Manager assigns task** via API:
   ```python
   TaskAutomationService.assign_task(
       db=db,
       assigner_id=manager_id,
       assignee_id=employee_id,
       ...
   )
   ```

2. **Service creates records** in single transaction:
   - Insert into `work_assignments` table
   - Insert into `tasks` table (triggers pg_notify)
   - Insert into `inbox_notifications` table
   - Insert into `audit_logs` table

3. **PostgreSQL trigger fires**:
   ```sql
   -- trg_emit_task_event fires on tasks insert
   NOTIFY tasks_events, '{"event_type":"task_assigned","entity_id":123,...}'
   ```

4. **PostgreSQL Listener receives NOTIFY**:
   - Parses payload
   - Publishes to Redis channel `tasks_events`
   - Routes to worker queues based on priority

5. **WebSocket Broadcaster** receives Redis event:
   - Looks up recipient user IDs
   - Publishes to user-specific channel `user:456:events`

6. **Connected WebSocket client** receives event instantly:
   ```json
   {
     "type": "task_assigned",
     "title": "New Task Assigned",
     "body": "You've been assigned: Fix login bug",
     "entity_type": "task",
     "entity_id": 123
   }
   ```

7. **Notification Workers** process async delivery:
   - Email worker sends email notification
   - Slack worker posts to user's Slack channel
   - Push worker sends mobile push notification

8. **Delivery tracking**:
   - Update `inbox_notifications.delivery_channel` = `["email", "slack", "push", "websocket"]`
   - Record delivery timestamps
   - Track failures and retries

## Running the System

### Prerequisites

```bash
# Install dependencies
pip install asyncpg redis python-socketio aioredis

# Set environment variables
DATABASE_URL=postgresql://postgres:password@localhost:5432/hrms
REDIS_URL=redis://localhost:6379/0
```

### Start Workers

```bash
# Terminal 1: Run notification workers
cd hrms_backend
python run_workers.py
```

### Start FastAPI Server

```bash
# Terminal 2: Run FastAPI app
cd hrms_backend
uvicorn app.main:app --reload --port 8000
```

### Test WebSocket Connection

```javascript
// Frontend JavaScript
const token = 'your_jwt_token';
const ws = new WebSocket(`ws://localhost:8000/api/ws/notifications?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  if (data.type === 'notification') {
    // Show toast notification
    showToast(data.title, data.body);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

## Monitoring

### Check Worker Status

```bash
# Check if workers are running
ps aux | grep run_workers

# View worker logs
tail -f logs/workers.log
```

### Check Redis

```bash
# Connect to Redis CLI
redis-cli

# Check pub/sub channels
PUBSUB CHANNELS
PUBSUB NUMSUB tasks_events

# Check queue lengths
ZCARD queue:email
ZCARD queue:websocket

# Check connected WebSocket users
HGETALL ws:connections
```

### Check PostgreSQL NOTIFY

```sql
-- In psql
LISTEN tasks_events;

-- In another terminal, insert a task
INSERT INTO tasks (...) VALUES (...);

-- First terminal should show NOTIFY
```

## Scaling

### Horizontal Scaling

The architecture supports multiple worker instances:

```bash
# Run multiple worker processes
python run_workers.py --workers 4
```

Workers coordinate via Redis:
- No duplicate processing (queue-based)
- Load balancing across workers
- Distributed connection tracking

### Performance Tuning

**Redis**:
```bash
# Increase max clients
redis-cli CONFIG SET maxclients 10000

# Enable persistence if needed
redis-cli CONFIG SET save "900 1 300 10"
```

**PostgreSQL**:
```sql
-- Increase max connections
ALTER SYSTEM SET max_connections = 200;

-- Tune for NOTIFY
ALTER SYSTEM SET max_notify_queue_pages = 10;
```

**Worker Pool**:
```python
# Adjust worker count based on load
NOTIFICATION_WORKERS = 4
EMAIL_WORKERS = 2
WEBSOCKET_WORKERS = 2
```

## Error Handling

### Retry Logic

Failed notifications are retried with exponential backoff:

1. **Attempt 1**: Immediate
2. **Attempt 2**: 5 seconds
3. **Attempt 3**: 30 seconds
4. **Attempt 4**: 5 minutes

After max retries, notification is marked as failed and logged.

### Dead Letter Queue

Failed notifications after max retries go to:
- `queue:failed` in Redis
- Can be manually reprocessed or investigated

### Health Checks

```python
# Check Redis connection
GET /api/health/redis

# Check PostgreSQL connection
GET /api/health/postgres

# Check WebSocket status
GET /api/ws/status
```

## Security

### WebSocket Authentication

- JWT token required for connection
- Token can be passed via query parameter or initial message
- Invalid tokens are rejected (code 1008)
- Connections expire after 24 hours

### Rate Limiting

- Implemented per user per window
- Redis keys: `ratelimit:{window}:{user_id}`
- Default: 100 events/minute per user

### Message Validation

- All events validated before broadcasting
- Recipient verification (users only see their events)
- Metadata sanitization

## Troubleshooting

### No events received in WebSocket

1. Check if workers are running: `ps aux | grep run_workers`
2. Check Redis connection: `redis-cli PING`
3. Check PostgreSQL LISTEN: `SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';`
4. Verify triggers are active: `\df+ emit_*` in psql

### Emails not sending

1. Check email queue: `redis-cli ZCARD queue:email`
2. Check email worker logs
3. Verify SMTP configuration
4. Check retry count: `redis-cli GET notification:retry:{id}`

### High latency

1. Check Redis queue sizes
2. Add more worker instances
3. Tune PostgreSQL `max_notify_queue_pages`
4. Add database indexes on entity_id columns

## Future Enhancements

- [ ] Bull/BullMQ integration for advanced queue management
- [ ] Message batching for high-volume events
- [ ] Event replay/rewind capabilities
- [ ] GraphQL subscriptions support
- [ ] Multi-tenant isolation
- [ ] Metrics dashboard (Grafana)
- [ ] Distributed tracing (OpenTelemetry)

-- 0001_create_notifications_schema.sql
-- Creates core tables for notifications, RBAC, and websocket mapping
-- Includes PL/pgSQL trigger functions that emit NOTIFY events for downstream workers

BEGIN;

-- 1. employees table
CREATE TABLE IF NOT EXISTS employees (
    employee_id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NULL, -- optional link to auth users table
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role_id TEXT NOT NULL, -- e.g., 'employee','manager','hr_admin','super_admin'
    department_id TEXT NULL,
    reporting_manager_id INTEGER NULL REFERENCES employees(employee_id) ON DELETE SET NULL,
    employment_status TEXT DEFAULT 'active',
    notification_preferences JSONB DEFAULT '{}'::jsonb,
    max_workload_hours NUMERIC DEFAULT 40,
    current_workload_hours NUMERIC DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 2. role_permissions table (RBAC core)
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_name TEXT NOT NULL,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    scope TEXT NOT NULL, -- own/team/department/all
    conditions JSONB NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 3. messages table
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id INTEGER NULL REFERENCES employees(employee_id) ON DELETE SET NULL,
    subject TEXT NULL,
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'direct', -- direct, broadcast, system
    priority TEXT DEFAULT 'normal',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 4. broadcast_messages table
CREATE TABLE IF NOT EXISTS broadcast_messages (
    broadcast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(message_id) ON DELETE CASCADE,
    target_type TEXT NOT NULL, -- 'role','department','all','custom'
    target_value TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 5. inbox_notifications table
CREATE TABLE IF NOT EXISTS inbox_notifications (
    inbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
    notification_type TEXT DEFAULT 'message', -- message,task,leave,approval
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE NULL,
    delivered_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    delivery_channel JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 6. tasks table
CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NULL,
    assigned_by INTEGER NULL REFERENCES employees(employee_id) ON DELETE SET NULL,
    assigned_to INTEGER NULL REFERENCES employees(employee_id) ON DELETE SET NULL,
    status TEXT DEFAULT 'assigned', -- assigned, in_progress, completed
    priority TEXT DEFAULT 'medium',
    estimated_hours NUMERIC NULL,
    actual_hours NUMERIC DEFAULT 0,
    due_date DATE NULL,
    progress_percentage INTEGER DEFAULT 0,
    project_name TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 7. leave_requests table
CREATE TABLE IF NOT EXISTS leave_requests (
    leave_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id INTEGER NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    approver_id INTEGER NULL REFERENCES employees(employee_id) ON DELETE SET NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_type TEXT NOT NULL,
    reason TEXT NULL,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 8. audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id INTEGER NULL REFERENCES employees(employee_id),
    action_type TEXT NOT NULL,
    resource_type TEXT NULL,
    resource_id TEXT NULL,
    target_user_id INTEGER NULL REFERENCES employees(employee_id),
    old_value JSONB NULL,
    new_value JSONB NULL,
    request_source TEXT NULL,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 9. websocket_connections table
CREATE TABLE IF NOT EXISTS websocket_connections (
    conn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    socket_id TEXT NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_inbox_user ON inbox_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_leave_approver ON leave_requests(approver_id);

-- EXTENSIONS required
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Trigger functions for notifications (emit pg_notify)

-- Function: emit_message_event
CREATE OR REPLACE FUNCTION emit_message_event() RETURNS TRIGGER AS $$
DECLARE
    payload json;
BEGIN
    payload = json_build_object(
        'event_type', 'MESSAGE_SENT',
        'message_id', NEW.message_id,
        'sender_id', NEW.sender_id,
        'message_type', NEW.message_type,
        'priority', NEW.priority
    );
    PERFORM pg_notify('new_message', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function: emit_inbox_event
CREATE OR REPLACE FUNCTION emit_inbox_event() RETURNS TRIGGER AS $$
DECLARE
    payload json;
BEGIN
    payload = json_build_object(
        'event_type', 'INBOX_NOTIFICATION',
        'inbox_id', NEW.inbox_id,
        'message_id', NEW.message_id,
        'user_id', NEW.user_id,
        'notification_type', NEW.notification_type
    );
    PERFORM pg_notify('inbox_update_' || NEW.user_id, payload::text);
    -- Also send a generic channel for workers
    PERFORM pg_notify('inbox_update', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function: emit_task_event
CREATE OR REPLACE FUNCTION emit_task_event() RETURNS TRIGGER AS $$
DECLARE
    payload json;
BEGIN
    payload = json_build_object(
        'event_type', 'TASK_ASSIGNED',
        'task_id', NEW.task_id,
        'assigned_by', NEW.assigned_by,
        'assigned_to', NEW.assigned_to,
        'title', NEW.title
    );
    PERFORM pg_notify('task_events', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function: emit_leave_event
CREATE OR REPLACE FUNCTION emit_leave_event() RETURNS TRIGGER AS $$
DECLARE
    payload json;
BEGIN
    payload = json_build_object(
        'event_type', 'LEAVE_EVENT',
        'leave_id', NEW.leave_id,
        'employee_id', NEW.employee_id,
        'approver_id', NEW.approver_id,
        'status', NEW.status
    );
    PERFORM pg_notify('leave_events', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trg_emit_message_event ON messages;
CREATE TRIGGER trg_emit_message_event
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE PROCEDURE emit_message_event();

DROP TRIGGER IF EXISTS trg_emit_inbox_event ON inbox_notifications;
CREATE TRIGGER trg_emit_inbox_event
AFTER INSERT ON inbox_notifications
FOR EACH ROW
EXECUTE PROCEDURE emit_inbox_event();

DROP TRIGGER IF EXISTS trg_emit_task_event ON tasks;
CREATE TRIGGER trg_emit_task_event
AFTER INSERT ON tasks
FOR EACH ROW
EXECUTE PROCEDURE emit_task_event();

DROP TRIGGER IF EXISTS trg_emit_leave_event ON leave_requests;
CREATE TRIGGER trg_emit_leave_event
AFTER INSERT ON leave_requests
FOR EACH ROW
EXECUTE PROCEDURE emit_leave_event();

COMMIT;

-- NOTE:
-- This migration creates the core schema and triggers. It is recommended to run under a migration tool
-- (Alembic) and to further harden RLS policies and permissions post-deployment.

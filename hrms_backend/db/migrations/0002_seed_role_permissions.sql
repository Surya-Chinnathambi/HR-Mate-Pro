-- 0002_seed_role_permissions.sql
-- Seeds the role_permissions table with sensible defaults for common roles
-- This allows the RBAC system to enforce authorization policies

BEGIN;

-- Clean existing permissions (optional - remove if you want to preserve custom permissions)
-- DELETE FROM role_permissions;

-- ============================================================================
-- EMPLOYEE ROLE (scope: own)
-- Employees can manage their own data
-- ============================================================================

-- Attendance: employees can clock in/out for themselves
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('employee', 'attendance', 'clock_in', 'own', NULL),
    ('employee', 'attendance', 'clock_out', 'own', NULL),
    ('employee', 'attendance', 'view', 'own', NULL),
    ('employee', 'attendance', 'regularize', 'own', NULL);

-- Leave: employees can apply for their own leave
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('employee', 'leave_application', 'create', 'own', NULL),
    ('employee', 'leave_application', 'view', 'own', NULL),
    ('employee', 'leave_application', 'cancel', 'own', '{"status": ["pending", "approved"]}');

-- Tasks: employees can view and update tasks assigned to them
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('employee', 'work_assignment', 'view', 'own', NULL),
    ('employee', 'work_assignment', 'update_status', 'own', NULL),
    ('employee', 'work_assignment', 'log_time', 'own', NULL),
    ('employee', 'work_assignment', 'comment', 'own', NULL);

-- Messages: employees can view their own inbox
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('employee', 'message', 'view', 'own', NULL),
    ('employee', 'message', 'mark_read', 'own', NULL);

-- Profile: employees can view and update their own profile
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('employee', 'profile', 'view', 'own', NULL),
    ('employee', 'profile', 'update', 'own', NULL);


-- ============================================================================
-- MANAGER ROLE (scope: team)
-- Managers inherit employee permissions + team management capabilities
-- ============================================================================

-- Managers inherit all employee permissions (insert duplicates with role_name='manager')
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'attendance', 'clock_in', 'own', NULL),
    ('manager', 'attendance', 'clock_out', 'own', NULL),
    ('manager', 'attendance', 'view', 'own', NULL),
    ('manager', 'leave_application', 'create', 'own', NULL),
    ('manager', 'leave_application', 'view', 'own', NULL),
    ('manager', 'work_assignment', 'view', 'own', NULL),
    ('manager', 'work_assignment', 'update_status', 'own', NULL),
    ('manager', 'message', 'view', 'own', NULL),
    ('manager', 'profile', 'view', 'own', NULL),
    ('manager', 'profile', 'update', 'own', NULL);

-- Managers can view team attendance and approve regularizations
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'attendance', 'view', 'team', NULL),
    ('manager', 'attendance', 'approve_regularization', 'team', NULL);

-- Managers can approve/reject team leave applications
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'leave_application', 'view', 'team', NULL),
    ('manager', 'leave_application', 'approve', 'team', NULL),
    ('manager', 'leave_application', 'reject', 'team', NULL);

-- Managers can create and assign tasks to their team
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'work_assignment', 'create', 'team', '{"max_assignee_workload_hours": 50}'),
    ('manager', 'work_assignment', 'view', 'team', NULL),
    ('manager', 'work_assignment', 'update', 'team', NULL),
    ('manager', 'work_assignment', 'delete', 'team', NULL),
    ('manager', 'work_assignment', 'reassign', 'team', NULL);

-- Managers can send messages to their team
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'message', 'send', 'team', NULL),
    ('manager', 'message', 'broadcast', 'team', NULL);

-- Managers can view team member profiles
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('manager', 'profile', 'view', 'team', NULL);


-- ============================================================================
-- HR ROLE (scope: department or all)
-- HR can manage leave, attendance, and employee records across departments
-- ============================================================================

-- HR inherits employee permissions
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'attendance', 'clock_in', 'own', NULL),
    ('hr', 'attendance', 'clock_out', 'own', NULL),
    ('hr', 'leave_application', 'create', 'own', NULL),
    ('hr', 'message', 'view', 'own', NULL),
    ('hr', 'profile', 'view', 'own', NULL);

-- HR can view and manage attendance for all employees
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'attendance', 'view', 'all', NULL),
    ('hr', 'attendance', 'approve_regularization', 'all', NULL),
    ('hr', 'attendance', 'edit', 'all', NULL);

-- HR can view and approve leave applications for all
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'leave_application', 'view', 'all', NULL),
    ('hr', 'leave_application', 'approve', 'all', NULL),
    ('hr', 'leave_application', 'reject', 'all', NULL),
    ('hr', 'leave_application', 'cancel', 'all', NULL);

-- HR can view all tasks (for workload monitoring)
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'work_assignment', 'view', 'all', NULL);

-- HR can send messages and broadcasts to all employees
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'message', 'send', 'all', NULL),
    ('hr', 'message', 'broadcast', 'all', NULL),
    ('hr', 'message', 'view', 'all', NULL);

-- HR can view and manage all employee profiles
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('hr', 'profile', 'view', 'all', NULL),
    ('hr', 'profile', 'update', 'all', NULL),
    ('hr', 'profile', 'create', 'all', NULL);


-- ============================================================================
-- ADMIN ROLE (scope: all)
-- Admins have full access to all resources
-- ============================================================================

-- Admin can do everything
INSERT INTO role_permissions (role_name, resource, action, scope, conditions)
VALUES 
    ('admin', 'attendance', 'view', 'all', NULL),
    ('admin', 'attendance', 'edit', 'all', NULL),
    ('admin', 'attendance', 'delete', 'all', NULL),
    ('admin', 'leave_application', 'view', 'all', NULL),
    ('admin', 'leave_application', 'approve', 'all', NULL),
    ('admin', 'leave_application', 'reject', 'all', NULL),
    ('admin', 'leave_application', 'delete', 'all', NULL),
    ('admin', 'work_assignment', 'view', 'all', NULL),
    ('admin', 'work_assignment', 'create', 'all', NULL),
    ('admin', 'work_assignment', 'update', 'all', NULL),
    ('admin', 'work_assignment', 'delete', 'all', NULL),
    ('admin', 'message', 'view', 'all', NULL),
    ('admin', 'message', 'send', 'all', NULL),
    ('admin', 'message', 'broadcast', 'all', NULL),
    ('admin', 'message', 'delete', 'all', NULL),
    ('admin', 'profile', 'view', 'all', NULL),
    ('admin', 'profile', 'create', 'all', NULL),
    ('admin', 'profile', 'update', 'all', NULL),
    ('admin', 'profile', 'delete', 'all', NULL),
    ('admin', 'role_permissions', 'view', 'all', NULL),
    ('admin', 'role_permissions', 'create', 'all', NULL),
    ('admin', 'role_permissions', 'update', 'all', NULL),
    ('admin', 'role_permissions', 'delete', 'all', NULL);

COMMIT;

-- NOTE:
-- This seed migration provides a baseline RBAC configuration. You can:
-- 1. Extend permissions by adding more rows for specific use cases
-- 2. Use conditions JSONB to add fine-grained rules (e.g., workload limits, date restrictions)
-- 3. Adjust scopes as needed (own/team/department/all)
-- 4. Run this as part of your deployment or via the apply_migrations.py helper

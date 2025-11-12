"""Add enterprise HRMS features: approval chains, work assignments, org hierarchy

Revision ID: 005
Revises: 004
Create Date: 2025-11-11 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add enterprise features: approval chains, work assignments, organizational hierarchy"""
    
    # ========================================================================
    # 1. APPROVAL CHAIN TABLES
    # ========================================================================
    
    # Create approval_chains table
    op.create_table(
        'approval_chains',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('request_type', sa.String(50), nullable=False, index=True),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True, index=True),
        sa.Column('level', sa.Integer(), nullable=False, index=True),
        sa.Column('approval_role', sa.String(50), nullable=False, index=True),
        sa.Column('approver_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True),
        sa.Column('min_amount', sa.Float(), nullable=True),
        sa.Column('max_amount', sa.Float(), nullable=True),
        sa.Column('min_days', sa.Integer(), nullable=True),
        sa.Column('max_days', sa.Integer(), nullable=True),
        sa.Column('escalation_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('reminder_hours', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('parallel_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    
    op.create_index('idx_approval_chain_lookup', 'approval_chains', ['request_type', 'department_id', 'level'])
    
    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(100), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('requester_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('request_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('current_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('days', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, index=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_reminder_sent', sa.DateTime(), nullable=True),
        sa.Column('escalation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('idx_approval_entity', 'approval_requests', ['entity_type', 'entity_id'])
    op.create_index('idx_approval_status_date', 'approval_requests', ['status', 'requested_at'])
    
    # Create approval_steps table
    op.create_table(
        'approval_steps',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('approval_request_id', sa.Integer(), sa.ForeignKey('approval_requests.id'), nullable=False, index=True),
        sa.Column('level', sa.Integer(), nullable=False, index=True),
        sa.Column('approver_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('approval_role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('comments', sa.String(1000), nullable=True),
        sa.Column('escalated_from_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True),
        sa.Column('escalated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('idx_approval_step_status', 'approval_steps', ['approver_id', 'status'])
    
    # ========================================================================
    # 2. ORGANIZATIONAL HIERARCHY TABLES
    # ========================================================================
    
    # Create reporting_relationships table
    op.create_table(
        'reporting_relationships',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('relationship_type', sa.String(20), nullable=False, server_default='direct'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('context', sa.String(200), nullable=True),
        sa.Column('effective_from', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('can_approve_leave', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_approve_expenses', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_approve_timesheets', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_assign_work', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    
    op.create_index('idx_reporting_employee', 'reporting_relationships', ['employee_id', 'is_active'])
    op.create_index('idx_reporting_manager', 'reporting_relationships', ['manager_id', 'is_active'])
    
    # ========================================================================
    # 3. WORK ASSIGNMENT TABLES
    # ========================================================================
    
    # Create work_assignments table
    op.create_table(
        'work_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('assigner_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('assignee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium', index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='not_started', index=True),
        sa.Column('assigned_date', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False, index=True),
        sa.Column('due_date', sa.Date(), nullable=True, index=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=False, server_default='0'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completion_notes', sa.String(1000), nullable=True),
        sa.Column('depends_on_task_id', sa.Integer(), sa.ForeignKey('work_assignments.id'), nullable=True),
        sa.Column('blocks_task_ids', sa.String(200), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_status_update', sa.DateTime(), nullable=True),
        sa.Column('project_name', sa.String(200), nullable=True, index=True),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('ai_suggested', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('delegated_from_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True),
        sa.Column('delegation_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    op.create_index('idx_work_assignment_assignee_status', 'work_assignments', ['assignee_id', 'status', 'due_date'])
    op.create_index('idx_work_assignment_assigner', 'work_assignments', ['assigner_id', 'assigned_date'])
    op.create_index('idx_work_assignment_project', 'work_assignments', ['project_name', 'status'])
    
    # Create task_comments table
    op.create_table(
        'task_comments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('work_assignments.id'), nullable=False, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('comment', sa.String(2000), nullable=False),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('mentioned_employee_ids', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Create task_time_logs table
    op.create_table(
        'task_time_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('work_assignments.id'), nullable=False, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('log_date', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False, index=True),
        sa.Column('hours_logged', sa.Float(), nullable=False),
        sa.Column('work_description', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('idx_time_log_task_date', 'task_time_logs', ['task_id', 'log_date'])
    
    # ========================================================================
    # 4. AUDIT LOG TABLE
    # ========================================================================
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('entity_type', sa.String(100), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('old_value', JSONB, nullable=True),
        sa.Column('new_value', JSONB, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True, index=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False, index=True),
        sa.Column('is_policy_violation', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('violation_reason', sa.String(500), nullable=True),
    )
    
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action', 'timestamp'])
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_violations', 'audit_logs', ['is_policy_violation', 'timestamp'])
    
    # ========================================================================
    # 5. ADD NEW COLUMNS TO EXISTING TABLES
    # ========================================================================
    
    # Add enterprise columns to employees table
    op.add_column('employees', sa.Column('reporting_manager_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True))
    op.add_column('employees', sa.Column('is_manager', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('employees', sa.Column('can_approve_leave', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('employees', sa.Column('can_approve_expenses', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('employees', sa.Column('can_approve_timesheets', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('employees', sa.Column('approval_limit_amount', sa.Float(), nullable=True))
    op.add_column('employees', sa.Column('notification_preferences', JSONB, nullable=True))
    op.add_column('employees', sa.Column('current_workload_hours', sa.Float(), nullable=False, server_default='0'))
    op.add_column('employees', sa.Column('max_workload_hours', sa.Float(), nullable=False, server_default='40'))
    op.add_column('employees', sa.Column('skills', sa.String(1000), nullable=True))
    op.add_column('employees', sa.Column('expertise_areas', sa.String(1000), nullable=True))
    
    # Add indexes on new employee columns
    op.create_index('idx_employee_reporting_manager', 'employees', ['reporting_manager_id'])
    op.create_index('idx_employee_is_manager', 'employees', ['is_manager'])
    
    # Add enterprise columns to departments table
    op.add_column('departments', sa.Column('parent_department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True))
    op.add_column('departments', sa.Column('hr_contact_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=True))
    op.add_column('departments', sa.Column('cost_center_code', sa.String(50), nullable=True))
    
    op.create_index('idx_department_parent', 'departments', ['parent_department_id'])


def downgrade():
    """Remove enterprise features"""
    
    # Drop indexes
    op.drop_index('idx_department_parent', table_name='departments')
    op.drop_index('idx_employee_is_manager', table_name='employees')
    op.drop_index('idx_employee_reporting_manager', table_name='employees')
    
    # Drop columns from existing tables
    op.drop_column('departments', 'cost_center_code')
    op.drop_column('departments', 'hr_contact_id')
    op.drop_column('departments', 'parent_department_id')
    
    op.drop_column('employees', 'expertise_areas')
    op.drop_column('employees', 'skills')
    op.drop_column('employees', 'max_workload_hours')
    op.drop_column('employees', 'current_workload_hours')
    op.drop_column('employees', 'notification_preferences')
    op.drop_column('employees', 'approval_limit_amount')
    op.drop_column('employees', 'can_approve_timesheets')
    op.drop_column('employees', 'can_approve_expenses')
    op.drop_column('employees', 'can_approve_leave')
    op.drop_column('employees', 'is_manager')
    op.drop_column('employees', 'reporting_manager_id')
    
    # Drop audit logs table
    op.drop_index('idx_audit_violations', table_name='audit_logs')
    op.drop_index('idx_audit_entity', table_name='audit_logs')
    op.drop_index('idx_audit_user_action', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    # Drop work assignment tables
    op.drop_index('idx_time_log_task_date', table_name='task_time_logs')
    op.drop_table('task_time_logs')
    op.drop_table('task_comments')
    op.drop_index('idx_work_assignment_project', table_name='work_assignments')
    op.drop_index('idx_work_assignment_assigner', table_name='work_assignments')
    op.drop_index('idx_work_assignment_assignee_status', table_name='work_assignments')
    op.drop_table('work_assignments')
    
    # Drop reporting relationships table
    op.drop_index('idx_reporting_manager', table_name='reporting_relationships')
    op.drop_index('idx_reporting_employee', table_name='reporting_relationships')
    op.drop_table('reporting_relationships')
    
    # Drop approval tables
    op.drop_index('idx_approval_step_status', table_name='approval_steps')
    op.drop_table('approval_steps')
    op.drop_index('idx_approval_status_date', table_name='approval_requests')
    op.drop_index('idx_approval_entity', table_name='approval_requests')
    op.drop_table('approval_requests')
    op.drop_index('idx_approval_chain_lookup', table_name='approval_chains')
    op.drop_table('approval_chains')

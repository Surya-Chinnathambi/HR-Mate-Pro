"""
Create chat conversation and message tables

Revision ID: 006
Revises: 005
Create Date: 2025-11-11 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '006'
down_revision = '005'  # Previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_conversations table
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('summary', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index(
        'ix_chat_conversations_employee_id',
        'chat_conversations',
        ['employee_id']
    )
    op.create_index(
        'ix_chat_conversations_is_active',
        'chat_conversations',
        ['employee_id', 'is_active']
    )
    op.create_index(
        'ix_chat_conversations_last_message',
        'chat_conversations',
        ['employee_id', 'last_message_at']
    )

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.JSON(), nullable=False),  # USER, ASSISTANT, SYSTEM
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(length=10000), nullable=False),
        sa.Column('function_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('function_args', sa.JSON(), nullable=True),
        sa.Column('function_result', sa.JSON(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model_used', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for message queries
    op.create_index(
        'ix_chat_messages_conversation_id',
        'chat_messages',
        ['conversation_id']
    )
    op.create_index(
        'ix_chat_messages_created_at',
        'chat_messages',
        ['conversation_id', 'created_at']
    )
    
    # Add team_id to employees table for team isolation
    op.add_column(
        'employees',
        sa.Column('team_id', sa.Integer(), nullable=True)
    )
    
    # Add role to employees for role-based dashboards
    op.add_column(
        'employees',
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='employee')
    )
    # role can be: 'employee', 'manager', 'hr', 'admin'
    
    # Create index for team queries
    op.create_index(
        'ix_employees_team_id',
        'employees',
        ['team_id']
    )
    op.create_index(
        'ix_employees_role',
        'employees',
        ['role']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_employees_role', table_name='employees')
    op.drop_index('ix_employees_team_id', table_name='employees')
    op.drop_index('ix_chat_messages_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_index('ix_chat_conversations_last_message', table_name='chat_conversations')
    op.drop_index('ix_chat_conversations_is_active', table_name='chat_conversations')
    op.drop_index('ix_chat_conversations_employee_id', table_name='chat_conversations')
    
    # Drop tables
    op.drop_table('chat_messages')
    op.drop_table('chat_conversations')
    
    # Drop columns
    op.drop_column('employees', 'role')
    op.drop_column('employees', 'team_id')

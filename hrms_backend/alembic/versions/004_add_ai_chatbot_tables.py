"""Add AI chatbot tables for conversation history and context

Revision ID: 004
Revises: 
Create Date: 2025-11-11 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '004'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(100), nullable=True),
        sa.Column('entities', JSONB, nullable=True),
        sa.Column('function_called', sa.String(100), nullable=True),
        sa.Column('function_params', JSONB, nullable=True),
        sa.Column('function_response', JSONB, nullable=True),
        sa.Column('policy_applied', sa.String(200), nullable=True),
        sa.Column('action_status', sa.String(50), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_conversation_history_conversation_id', 'conversation_history', ['conversation_id'])
    op.create_index('idx_conversation_history_user_id', 'conversation_history', ['user_id'])
    op.create_index('idx_conversation_history_created_at', 'conversation_history', ['created_at'])
    
    # Create AI chat sessions table
    op.create_table(
        'ai_chat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_start', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('session_end', sa.DateTime(), nullable=True),
        sa.Column('total_messages', sa.Integer(), default=0),
        sa.Column('intents_handled', JSONB, nullable=True),
        sa.Column('satisfaction_score', sa.Float(), nullable=True),
        sa.Column('escalated_to_human', sa.Boolean(), default=False),
        sa.Column('metadata', JSONB, nullable=True),
    )
    
    op.create_index('idx_ai_chat_sessions_user_id', 'ai_chat_sessions', ['user_id'])
    op.create_index('idx_ai_chat_sessions_session_start', 'ai_chat_sessions', ['session_start'])
    
    # Create function call audit table
    op.create_table(
        'ai_function_calls',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('function_name', sa.String(100), nullable=False),
        sa.Column('parameters', JSONB, nullable=False),
        sa.Column('response', JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('policy_checks', JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    op.create_index('idx_ai_function_calls_conversation_id', 'ai_function_calls', ['conversation_id'])
    op.create_index('idx_ai_function_calls_user_id', 'ai_function_calls', ['user_id'])
    op.create_index('idx_ai_function_calls_function_name', 'ai_function_calls', ['function_name'])
    op.create_index('idx_ai_function_calls_created_at', 'ai_function_calls', ['created_at'])


def downgrade():
    op.drop_table('ai_function_calls')
    op.drop_table('ai_chat_sessions')
    op.drop_table('conversation_history')

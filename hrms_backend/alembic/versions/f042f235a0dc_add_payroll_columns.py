"""add_payroll_columns

Revision ID: f042f235a0dc
Revises: 006
Create Date: 2025-11-12 21:56:20.541485

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'f042f235a0dc'
down_revision = '006'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add salary component columns to payrolls table (only if they don't exist)
    if not column_exists('payrolls', 'basic_salary'):
        op.add_column('payrolls', sa.Column('basic_salary', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'hra'):
        op.add_column('payrolls', sa.Column('hra', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'special_allowance'):
        op.add_column('payrolls', sa.Column('special_allowance', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'transport_allowance'):
        op.add_column('payrolls', sa.Column('transport_allowance', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'medical_allowance'):
        op.add_column('payrolls', sa.Column('medical_allowance', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'other_allowances'):
        op.add_column('payrolls', sa.Column('other_allowances', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'gross_salary'):
        op.add_column('payrolls', sa.Column('gross_salary', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'gross_pay'):
        op.add_column('payrolls', sa.Column('gross_pay', sa.Float(), nullable=True))
    
    # Add deduction columns
    if not column_exists('payrolls', 'pf_employee'):
        op.add_column('payrolls', sa.Column('pf_employee', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'pf_employer'):
        op.add_column('payrolls', sa.Column('pf_employer', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'income_tax'):
        op.add_column('payrolls', sa.Column('income_tax', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'professional_tax'):
        op.add_column('payrolls', sa.Column('professional_tax', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'other_deductions'):
        op.add_column('payrolls', sa.Column('other_deductions', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'total_deductions'):
        op.add_column('payrolls', sa.Column('total_deductions', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'deductions'):
        op.add_column('payrolls', sa.Column('deductions', sa.Float(), nullable=True))
    
    # Add net salary columns
    if not column_exists('payrolls', 'net_salary'):
        op.add_column('payrolls', sa.Column('net_salary', sa.Float(), nullable=False, server_default='0'))
    if not column_exists('payrolls', 'net_pay'):
        op.add_column('payrolls', sa.Column('net_pay', sa.Float(), nullable=True))
    
    # Add payment details columns
    if not column_exists('payrolls', 'payment_mode'):
        op.add_column('payrolls', sa.Column('payment_mode', sa.String(), nullable=False, server_default='Bank Transfer'))
    if not column_exists('payrolls', 'status'):
        op.add_column('payrolls', sa.Column('status', sa.String(), nullable=False, server_default='Paid'))


def downgrade() -> None:
    # Remove all added columns
    op.drop_column('payrolls', 'status')
    op.drop_column('payrolls', 'payment_mode')
    op.drop_column('payrolls', 'net_pay')
    op.drop_column('payrolls', 'net_salary')
    op.drop_column('payrolls', 'deductions')
    op.drop_column('payrolls', 'total_deductions')
    op.drop_column('payrolls', 'other_deductions')
    op.drop_column('payrolls', 'professional_tax')
    op.drop_column('payrolls', 'income_tax')
    op.drop_column('payrolls', 'pf_employer')
    op.drop_column('payrolls', 'pf_employee')
    op.drop_column('payrolls', 'gross_pay')
    op.drop_column('payrolls', 'gross_salary')
    op.drop_column('payrolls', 'other_allowances')
    op.drop_column('payrolls', 'medical_allowance')
    op.drop_column('payrolls', 'transport_allowance')
    op.drop_column('payrolls', 'special_allowance')
    op.drop_column('payrolls', 'hra')
    op.drop_column('payrolls', 'basic_salary')

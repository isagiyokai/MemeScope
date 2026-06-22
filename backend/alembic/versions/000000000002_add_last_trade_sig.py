"""Add last_trade_sig to tokens

Revision ID: 000000000002
Revises: 000000000001
Create Date: 2026-06-22 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '000000000002'
down_revision = '000000000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tokens', sa.Column('last_trade_sig', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('tokens', 'last_trade_sig')

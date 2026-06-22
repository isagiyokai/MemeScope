"""Backfill composite_score=0.0 for wallets with NULL score

Revision ID: 000000000003
Revises: 000000000002
Create Date: 2026-06-22 00:00:00.000000+00:00

"""
from alembic import op

revision = '000000000003'
down_revision = '000000000002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE wallets SET composite_score = 0.0 WHERE composite_score IS NULL")


def downgrade() -> None:
    pass

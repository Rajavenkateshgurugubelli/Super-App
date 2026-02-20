"""Add is_admin to users

Revision ID: f3a1b9c04d2e
Revises: 6789dee5249a
Create Date: 2026-02-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a1b9c04d2e'
down_revision = '6789dee5249a'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite supports ADD COLUMN for nullable columns
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('is_admin')

"""Add webauthn_credentials table

Revision ID: a1b2c3d4e5f6
Revises: f3a1b9c04d2e
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'f3a1b9c04d2e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'webauthn_credentials',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('credential_id', sa.String(), nullable=False),
        sa.Column('public_key', sa.String(), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('credential_id'),
    )
    op.create_index('ix_webauthn_credentials_user_id', 'webauthn_credentials', ['user_id'])
    op.create_index('ix_webauthn_credentials_credential_id', 'webauthn_credentials', ['credential_id'])


def downgrade():
    op.drop_index('ix_webauthn_credentials_credential_id', table_name='webauthn_credentials')
    op.drop_index('ix_webauthn_credentials_user_id', table_name='webauthn_credentials')
    op.drop_table('webauthn_credentials')

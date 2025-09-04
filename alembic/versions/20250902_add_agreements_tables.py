"""add agreements + templates + tokens + mentor_apprentice active flag

Revision ID: 20250902_add_agreements
Revises: 
Create Date: 2025-09-02
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20250902_add_agreements'
# NOTE: Adjust this if new migrations are added before applying.
down_revision = '32429d86a3c5'
branch_labels = None
depends_on = None

def upgrade():
    # agreement_templates
    op.create_table(
        'agreement_templates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False, unique=True),
        sa.Column('markdown_source', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    # Use proper boolean literal for Postgres instead of integer 1
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('supersedes_version', sa.Integer(), nullable=True),
        sa.Column('author_user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # agreements
    op.create_table(
        'agreements',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('mentor_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('apprentice_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('apprentice_email', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
    sa.Column('apprentice_is_minor', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('parent_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('parent_email', sa.String(), nullable=True),
        sa.Column('fields_json', sa.JSON(), nullable=False),
        sa.Column('content_rendered', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('apprentice_signature_name', sa.String(), nullable=True),
        sa.Column('apprentice_signed_at', sa.DateTime(), nullable=True),
        sa.Column('parent_signature_name', sa.String(), nullable=True),
        sa.Column('parent_signed_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_agreements_status', 'agreements', ['status'])
    op.create_index('ix_agreements_mentor', 'agreements', ['mentor_id'])
    op.create_index('ix_agreements_apprentice_email', 'agreements', ['apprentice_email'])

    # agreement_tokens
    op.create_table(
        'agreement_tokens',
        sa.Column('token', sa.String(), primary_key=True),
        sa.Column('agreement_id', sa.String(), sa.ForeignKey('agreements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_type', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_agreement_tokens_type', 'agreement_tokens', ['token_type'])

    # mentor_apprentice active flag
    with op.batch_alter_table('mentor_apprentice') as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False))

    # NOTE: Insert initial template version (placeholder); actual seeding should occur in application init or separate migration.


def downgrade():
    with op.batch_alter_table('mentor_apprentice') as batch_op:
        batch_op.drop_column('active')
    op.drop_index('ix_agreement_tokens_type', table_name='agreement_tokens')
    op.drop_table('agreement_tokens')
    op.drop_index('ix_agreements_apprentice_email', table_name='agreements')
    op.drop_index('ix_agreements_mentor', table_name='agreements')
    op.drop_index('ix_agreements_status', table_name='agreements')
    op.drop_table('agreements')
    op.drop_table('agreement_templates')

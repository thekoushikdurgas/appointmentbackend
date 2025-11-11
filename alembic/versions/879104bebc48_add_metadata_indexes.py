"""Add metadata indexes

Revision ID: 879104bebc48
Revises: 20241109_000001
Create Date: 2025-11-10 19:34:47.985854
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '879104bebc48'
down_revision = '20241109_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_contacts_metadata_city', 'contacts_metadata', ['city'], unique=False)
    op.create_index('idx_contacts_metadata_state', 'contacts_metadata', ['state'], unique=False)
    op.create_index('idx_contacts_metadata_country', 'contacts_metadata', ['country'], unique=False)
    op.create_index('idx_companies_metadata_city', 'companies_metadata', ['city'], unique=False)
    op.create_index('idx_companies_metadata_state', 'companies_metadata', ['state'], unique=False)
    op.create_index('idx_companies_metadata_country', 'companies_metadata', ['country'], unique=False)
    op.create_index(
        'idx_companies_metadata_company_name_for_emails',
        'companies_metadata',
        ['company_name_for_emails'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_companies_metadata_company_name_for_emails', table_name='companies_metadata')
    op.drop_index('idx_companies_metadata_country', table_name='companies_metadata')
    op.drop_index('idx_companies_metadata_state', table_name='companies_metadata')
    op.drop_index('idx_companies_metadata_city', table_name='companies_metadata')
    op.drop_index('idx_contacts_metadata_country', table_name='contacts_metadata')
    op.drop_index('idx_contacts_metadata_state', table_name='contacts_metadata')
    op.drop_index('idx_contacts_metadata_city', table_name='contacts_metadata')


"""Text retention: record when a document's text was purged under its platform's terms.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents ADD COLUMN text_purged_at timestamptz;
        -- The retention job looks for unpurged documents of one platform by collection time.
        CREATE INDEX documents_retention_idx ON documents (platform, collected_at)
            WHERE text_purged_at IS NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX documents_retention_idx;
        ALTER TABLE documents DROP COLUMN text_purged_at;
        """
    )

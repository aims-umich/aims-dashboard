"""Topic tags on segments, and per-word explanations of predictions.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Topic ids from sentiment.topics, set at ingest and re-applied by `sentiment topics`.
        ALTER TABLE segments ADD COLUMN topics text[] NOT NULL DEFAULT '{}';
        CREATE INDEX segments_topics_idx ON segments USING gin (topics) WHERE relevance = 'relevant';

        -- Which words pushed a prediction toward positive (score > 0) or negative (score < 0).
        -- `spans` is a JSON list of [start, end, score] character offsets into the segment text.
        CREATE TABLE explanations (
            segment_id bigint      NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
            model_id   integer     NOT NULL REFERENCES models(id),
            spans      jsonb       NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (segment_id, model_id)
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE explanations;
        DROP INDEX segments_topics_idx;
        ALTER TABLE segments DROP COLUMN topics;
        """
    )

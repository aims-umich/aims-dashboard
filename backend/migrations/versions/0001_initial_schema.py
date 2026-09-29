"""Initial schema: documents, segments, models, predictions, ingest_state.

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE documents (
            id                 bigserial PRIMARY KEY,
            platform           text        NOT NULL,
            external_id        text        NOT NULL,
            kind               text        NOT NULL CHECK (kind IN ('post', 'comment', 'article', 'video')),
            parent_id          bigint      REFERENCES documents(id) ON DELETE CASCADE,
            url                text,
            author_handle      text,
            title              text,
            body               text,
            lang               text,
            published_at       timestamptz NOT NULL,
            collected_at       timestamptz NOT NULL DEFAULT now(),
            metrics            jsonb       NOT NULL DEFAULT '{}'::jsonb,
            metrics_updated_at timestamptz,
            origin             text        NOT NULL DEFAULT 'live' CHECK (origin IN ('live', 'backfill')),
            raw                jsonb,
            UNIQUE (platform, external_id)
        );
        CREATE INDEX documents_platform_published_idx ON documents (platform, published_at DESC);
        CREATE INDEX documents_parent_idx ON documents (parent_id) WHERE parent_id IS NOT NULL;

        -- A scorable span of a document: the whole post, or one sentence of an article.
        CREATE TABLE segments (
            id               bigserial PRIMARY KEY,
            document_id      bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            ordinal          integer NOT NULL,
            text             text    NOT NULL,
            relevance        text    NOT NULL CHECK (relevance IN ('relevant', 'excluded', 'non_english')),
            relevance_reason text,
            UNIQUE (document_id, ordinal)
        );
        CREATE INDEX segments_scorable_idx ON segments (id DESC) WHERE relevance = 'relevant';

        CREATE TABLE models (
            id         serial PRIMARY KEY,
            name       text        NOT NULL,
            revision   text        NOT NULL,
            backend    text        NOT NULL,
            is_active  boolean     NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (name, revision)
        );
        -- At most one model is shown on the dashboard at a time; others score in shadow mode.
        CREATE UNIQUE INDEX models_single_active_idx ON models ((true)) WHERE is_active;

        -- Canonical labels: 0 = negative, 1 = neutral, 2 = positive.
        CREATE TABLE predictions (
            segment_id bigint      NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
            model_id   integer     NOT NULL REFERENCES models(id),
            label      smallint    NOT NULL CHECK (label IN (0, 1, 2)),
            p_neg      real        NOT NULL,
            p_neu      real        NOT NULL,
            p_pos      real        NOT NULL,
            confidence real        NOT NULL,
            scored_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (segment_id, model_id)
        );
        CREATE INDEX predictions_model_scored_idx ON predictions (model_id, scored_at DESC);

        CREATE TABLE ingest_state (
            source               text PRIMARY KEY,
            cursor               jsonb       NOT NULL DEFAULT '{}'::jsonb,
            interval_s           integer,
            last_run_at          timestamptz,
            last_success_at      timestamptz,
            last_error           text,
            last_error_at        timestamptz,
            consecutive_failures integer     NOT NULL DEFAULT 0,
            items_last_run       integer,
            new_last_run         integer,
            updated_at           timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE ingest_state;
        DROP TABLE predictions;
        DROP TABLE models;
        DROP TABLE segments;
        DROP TABLE documents;
        """
    )

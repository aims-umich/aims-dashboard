"""The scorer: loads one classifier and keeps every relevant segment scored by it.

The queue is just a query: "relevant segments with no prediction from this model".
New work wakes the scorer through Postgres LISTEN/NOTIFY, with a periodic poll as a fallback,
and `FOR UPDATE SKIP LOCKED` makes it safe to run more than one scorer.
Because the queue is a query, model downtime, backfills, and model upgrades all use this same path.
"""

from __future__ import annotations

import logging
import signal
import threading
import time

import psycopg
from psycopg.types.json import Jsonb

from sentiment.classifier import Classifier, ModelInfo, build_classifier
from sentiment.config import Settings
from sentiment.db import NEW_SEGMENTS_CHANNEL, connect
from sentiment.observability import Heartbeat

log = logging.getLogger(__name__)

# Newest first, so live posts are scored within seconds even while a backfill is queued.
CLAIM_SQL = """
    SELECT s.id, s.text, d.collected_at
    FROM segments s
    JOIN documents d ON d.id = s.document_id
    WHERE s.relevance = 'relevant' AND s.text <> ''
      AND NOT EXISTS (SELECT 1 FROM predictions p WHERE p.segment_id = s.id AND p.model_id = %(model_id)s)
    ORDER BY s.id DESC
    LIMIT %(limit)s
    FOR UPDATE OF s SKIP LOCKED
"""

RECHECK_SQL = """
    SELECT id FROM unnest(%(ids)s::bigint[]) AS id
    WHERE NOT EXISTS (SELECT 1 FROM predictions p WHERE p.segment_id = id AND p.model_id = %(model_id)s)
"""

# Recent scored texts that the site lists (posts, comments and article sentences), newest first.
EXPLAIN_CLAIM_SQL = """
    SELECT s.id, s.text
    FROM segments s
    JOIN documents d ON d.id = s.document_id
    JOIN predictions p ON p.segment_id = s.id AND p.model_id = %(model_id)s
    WHERE s.relevance = 'relevant' AND s.text <> '' AND d.kind IN ('post', 'comment', 'article')
      AND d.published_at > now() - make_interval(days => %(days)s)
      AND NOT EXISTS (SELECT 1 FROM explanations e WHERE e.segment_id = s.id AND e.model_id = %(model_id)s)
    ORDER BY d.published_at DESC
    LIMIT %(limit)s
    FOR UPDATE OF s SKIP LOCKED
"""

EXPLAIN_INSERT_SQL = """
    INSERT INTO explanations (segment_id, model_id, spans) VALUES (%s, %s, %s)
    ON CONFLICT (segment_id, model_id) DO NOTHING
"""

INSERT_SQL = """
    INSERT INTO predictions (segment_id, model_id, label, p_neg, p_neu, p_pos, confidence)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (segment_id, model_id) DO NOTHING
"""

HEARTBEAT_EVERY_S = 300


def register_model(conn: psycopg.Connection, info: ModelInfo) -> int:
    """Insert the model row if needed; the first model ever registered becomes the active one."""
    with conn.transaction():
        row = conn.execute(
            """
            INSERT INTO models (name, revision, backend) VALUES (%s, %s, %s)
            ON CONFLICT (name, revision) DO UPDATE SET backend = EXCLUDED.backend
            RETURNING id
            """,
            (info.name, info.revision, info.backend),
        ).fetchone()
        model_id = int(row["id"])
        conn.execute(
            """
            UPDATE models SET is_active = true
            WHERE id = %s AND NOT EXISTS (SELECT 1 FROM models WHERE is_active)
            """,
            (model_id,),
        )
    return model_id


def score_batch(conn: psycopg.Connection, classifier: Classifier, model_id: int, limit: int) -> int:
    """Claim, score, and save one batch. Returns how many segments were scored."""
    with conn.transaction():
        rows = conn.execute(CLAIM_SQL, {"model_id": model_id, "limit": limit}).fetchall()
        if rows:
            # The claim's snapshot predates any rival scorer that committed while we waited for a lock,
            # so re-check with a fresh statement; we hold the row locks, so this answer is final.
            unscored = {
                row["id"]
                for row in conn.execute(
                    RECHECK_SQL, {"ids": [row["id"] for row in rows], "model_id": model_id}
                )
            }
            rows = [row for row in rows if row["id"] in unscored]
        if not rows:
            return 0
        started = time.monotonic()
        probs = classifier.predict([row["text"] for row in rows])
        elapsed = time.monotonic() - started
        values = []
        for row, p in zip(rows, probs, strict=True):
            label = max(range(3), key=lambda i: p[i])
            values.append((row["id"], model_id, label, p[0], p[1], p[2], max(p)))
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, values)
    oldest = min(row["collected_at"] for row in rows)
    log.info(
        "scored batch",
        extra={
            "count": len(rows),
            "seconds": round(elapsed, 3),
            "per_second": round(len(rows) / elapsed, 1) if elapsed else None,
            "max_queue_wait_s": round(time.time() - oldest.timestamp(), 1),
        },
    )
    return len(rows)


def explain_batch(
    conn: psycopg.Connection, classifier: Classifier, model_id: int, limit: int, days: int
) -> int:
    """Explain one batch of recent scored texts. Returns 0 when the classifier cannot explain."""
    explain = getattr(classifier, "explain", None)
    if explain is None:
        return 0
    with conn.transaction():
        rows = conn.execute(
            EXPLAIN_CLAIM_SQL, {"model_id": model_id, "limit": limit, "days": days}
        ).fetchall()
        if not rows:
            return 0
        spans = explain([row["text"] for row in rows])
        with conn.cursor() as cur:
            cur.executemany(
                EXPLAIN_INSERT_SQL,
                [
                    (row["id"], model_id, Jsonb([list(s) for s in found]))
                    for row, found in zip(rows, spans, strict=True)
                ],
            )
    return len(rows)


class Scorer:
    def __init__(self, settings: Settings, classifier: Classifier | None = None) -> None:
        self.settings = settings
        self.classifier = classifier or build_classifier(settings)
        self.heartbeat = Heartbeat(settings, "scorer")
        self.stopping = threading.Event()

    def stop(self, *_: object) -> None:
        self.stopping.set()

    def run(self) -> None:
        backoff = 1.0
        while not self.stopping.is_set():
            try:
                self._run_connected()
                backoff = 1.0
            except psycopg.OperationalError as exc:
                log.warning("database unavailable, retrying", extra={"error": str(exc), "retry_s": backoff})
                self.stopping.wait(backoff)
                backoff = min(backoff * 2, 60.0)

    def _run_connected(self) -> None:
        settings = self.settings
        with (
            connect(settings.database_url) as work,
            connect(settings.database_url, autocommit=True) as listener,
        ):
            model_id = register_model(work, self.classifier.info)
            listener.execute(f"LISTEN {NEW_SEGMENTS_CHANNEL}")
            log.info("scorer ready", extra={"model_id": model_id, "model": self.classifier.info.name})
            last_beat = 0.0
            while not self.stopping.is_set():
                scored = score_batch(work, self.classifier, model_id, settings.scorer_batch_size)
                if time.monotonic() - last_beat > HEARTBEAT_EVERY_S:
                    self.heartbeat.ping_sync()
                    last_beat = time.monotonic()
                if scored >= settings.scorer_batch_size:
                    continue  # More work is probably waiting; keep draining.
                # Scoring is caught up: spend the idle time on explanations, one small batch at a time,
                # checking for new posts to score between batches.
                if settings.scorer_explain and explain_batch(
                    work,
                    self.classifier,
                    model_id,
                    settings.scorer_explain_batch,
                    settings.scorer_explain_days,
                ):
                    continue
                self._wait_for_work(listener)

    def _wait_for_work(self, listener: psycopg.Connection) -> None:
        deadline = time.monotonic() + self.settings.scorer_poll_interval_s
        while not self.stopping.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            # Short slices keep shutdown responsive; any notification means new work.
            for _ in listener.notifies(timeout=min(remaining, 2.0), stop_after=1):
                return


def main(settings: Settings) -> None:
    scorer = Scorer(settings)
    signal.signal(signal.SIGTERM, scorer.stop)
    signal.signal(signal.SIGINT, scorer.stop)
    scorer.run()
    log.info("scorer stopped")

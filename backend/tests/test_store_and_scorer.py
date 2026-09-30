from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

import psycopg
import pytest

from sentiment.db import async_pool, connect
from sentiment.ingest import store
from sentiment.ingest.base import DocumentIn, PollResult, SegmentIn
from sentiment.scorer.service import Scorer, register_model, score_batch
from sentiment.text import classify_relevance
from tests.fake import FakeClassifier


def post(external_id: str, text: str, **kw) -> DocumentIn:
    return DocumentIn(
        platform=kw.pop("platform", "mastodon"),
        external_id=external_id,
        kind="post",
        published_at=kw.pop("published_at", datetime(2026, 9, 28, tzinfo=UTC)),
        body=text,
        segments=[SegmentIn(text, classify_relevance(text, lang="en"))],
        **kw,
    )


@pytest.fixture
async def pool(database_url, db):
    pool = await async_pool(database_url)
    yield pool
    await pool.close()


async def test_upserts_are_idempotent_and_refresh_metrics(pool, db):
    async with pool.connection() as conn, conn.transaction():
        first = await store.save_documents(conn, [post("a", "nuclear power is good", metrics={"likes": 1})])
    async with pool.connection() as conn, conn.transaction():
        again = await store.save_documents(conn, [post("a", "nuclear power is good", metrics={"likes": 5})])
    assert (first.new_documents, first.new_segments) == (1, 1)
    assert (again.new_documents, again.new_segments, again.updated_metrics) == (0, 0, 1)
    assert db.execute("SELECT count(*) AS n FROM segments").fetchone()["n"] == 1
    assert db.execute("SELECT metrics FROM documents").fetchone()["metrics"] == {"likes": 5}


async def test_commit_run_saves_cursor_notifies_and_honors_deletions(pool, db, database_url):
    listener = psycopg.connect(database_url, autocommit=True)
    listener.execute("LISTEN new_segments")
    async with pool.connection() as conn:
        await store.commit_run(conn, "mastodon", PollResult([post("a", "nuclear power")], {"k": "1"}, 1), 120)
    assert list(listener.notifies(timeout=2, stop_after=1))
    async with pool.connection() as conn:
        saved = await store.commit_run(
            conn, "mastodon", PollResult([], {"k": "2"}, 0, deletions=[("mastodon", "a")]), 120
        )
    listener.close()
    assert saved.deleted == 1
    assert db.execute("SELECT count(*) AS n FROM segments").fetchone()["n"] == 0
    state = db.execute("SELECT * FROM ingest_state").fetchone()
    assert state["cursor"] == {"k": "2"}
    assert state["consecutive_failures"] == 0 and state["last_success_at"] is not None


async def test_record_failure_counts_up_and_success_resets(pool, db):
    async with pool.connection() as conn:
        assert await store.record_failure(conn, "nyt", "boom", 3600) == 1
        assert await store.record_failure(conn, "nyt", "boom", 3600) == 2
        await store.commit_run(conn, "nyt", PollResult([], {}, 0), 3600)
    row = db.execute("SELECT consecutive_failures, last_error FROM ingest_state").fetchone()
    assert row == {"consecutive_failures": 0, "last_error": "boom"}


async def test_orphan_comments_are_skipped(pool, db):
    comment = post("c1", "nice", parent_external_id="missing-video", platform="youtube")
    async with pool.connection() as conn, conn.transaction():
        saved = await store.save_documents(conn, [comment])
    assert saved.new_documents == 0


def seed(db, texts: list[str]) -> None:
    for i, text in enumerate(texts):
        row = db.execute(
            "INSERT INTO documents (platform, external_id, kind, published_at)"
            " VALUES ('mastodon', %s, 'post', now()) RETURNING id",
            (f"d{i}",),
        ).fetchone()
        relevance = classify_relevance(text, lang="en")
        db.execute(
            "INSERT INTO segments (document_id, ordinal, text, relevance) VALUES (%s, 0, %s, %s)",
            (row["id"], text, relevance.status),
        )


def test_first_model_becomes_active_and_second_is_shadow(db):
    first = register_model(db, FakeClassifier("a").info)
    second = register_model(db, FakeClassifier("b").info)
    assert register_model(db, FakeClassifier("a").info) == first
    active = db.execute("SELECT id FROM models WHERE is_active").fetchall()
    assert [r["id"] for r in active] == [first] and second != first


def test_score_batch_scores_relevant_segments_newest_first(db):
    seed(db, ["old nuclear power is bad", "the nuclear option", "new nuclear power is good"])
    clf = FakeClassifier()
    model_id = register_model(db, clf.info)
    assert score_batch(db, clf, model_id, limit=1) == 1
    assert clf.calls == [["new nuclear power is good"]]
    assert score_batch(db, clf, model_id, limit=10) == 1
    assert score_batch(db, clf, model_id, limit=10) == 0  # the idiom is excluded, never queued
    rows = db.execute(
        "SELECT label, p_neg, p_neu, p_pos, confidence FROM predictions ORDER BY segment_id"
    ).fetchall()
    assert [r["label"] for r in rows] == [0, 2]
    assert rows[1]["confidence"] == pytest.approx(0.8)


def test_shadow_model_scores_the_same_segments_independently(db):
    seed(db, ["nuclear power is good"])
    active, shadow = FakeClassifier("active"), FakeClassifier("shadow")
    a_id, s_id = register_model(db, active.info), register_model(db, shadow.info)
    assert score_batch(db, active, a_id, 10) == 1
    assert score_batch(db, shadow, s_id, 10) == 1
    assert db.execute("SELECT count(*) AS n FROM predictions").fetchone()["n"] == 2


def test_two_scorers_never_score_the_same_segment(db, database_url):
    seed(db, [f"nuclear power {i}" for i in range(40)])
    clf = FakeClassifier()
    model_id = register_model(db, clf.info)
    totals = []

    def work():
        with connect(database_url) as conn:
            n = 0
            while scored := score_batch(conn, clf, model_id, 5):
                n += scored
            totals.append(n)

    threads = [threading.Thread(target=work) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(totals) == 40
    assert db.execute("SELECT count(*) AS n FROM predictions").fetchone()["n"] == 40


def test_scorer_wakes_on_notify(db, settings):
    settings.scorer_poll_interval_s = 60  # Only a NOTIFY can wake it within the test's time budget.
    scorer = Scorer(settings, classifier=FakeClassifier())
    thread = threading.Thread(target=scorer.run, daemon=True)
    thread.start()
    time.sleep(1.0)
    seed(db, ["nuclear power is good"])
    db.execute("NOTIFY new_segments")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if db.execute("SELECT count(*) AS n FROM predictions").fetchone()["n"]:
            break
        time.sleep(0.1)
    scorer.stop()
    thread.join(timeout=10)
    assert db.execute("SELECT count(*) AS n FROM predictions").fetchone()["n"] == 1
    assert not thread.is_alive()

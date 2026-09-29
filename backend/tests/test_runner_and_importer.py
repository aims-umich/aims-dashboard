from __future__ import annotations

import asyncio
import csv
import sqlite3
from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx
import pytest

from sentiment.db import async_pool
from sentiment.importer.legacy import documents_for, import_documents
from sentiment.ingest.base import DocumentIn, Job, PollResult, SegmentIn
from sentiment.ingest.runner import Runner
from sentiment.text import classify_relevance


class FlakyJob(Job):
    """Fails once with a message containing its secret, then succeeds."""

    name: ClassVar[str] = "flaky"
    platform: ClassVar[str] = "mastodon"
    calls = 0

    @property
    def interval_s(self) -> float:
        return 0.05

    def secrets(self) -> list[str]:
        return ["top-secret"]

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        FlakyJob.calls += 1
        if FlakyJob.calls == 1:
            raise RuntimeError("upstream said no to key top-secret")
        text = "nuclear power"
        doc = DocumentIn(
            platform="mastodon",
            external_id=f"p{FlakyJob.calls}",
            kind="post",
            published_at=datetime.now(UTC),
            segments=[SegmentIn(text, classify_relevance(text, lang="en"))],
        )
        return PollResult([doc], {"n": FlakyJob.calls}, 1)


async def test_runner_records_redacted_failure_then_recovers(settings, db, database_url, monkeypatch):
    monkeypatch.setattr("sentiment.ingest.runner.random.uniform", lambda a, b: 0 if a == 0 else 1)
    pool = await async_pool(database_url)
    async with httpx.AsyncClient() as client:
        runner = Runner(settings, pool, [FlakyJob(settings, client, pool)])
        task = asyncio.create_task(runner.run())
        for _ in range(100):
            await asyncio.sleep(0.05)
            if db.execute("SELECT count(*) AS n FROM documents").fetchone()["n"] >= 1:
                break
        runner.stopping.set()
        await task
    await pool.close()
    state = db.execute("SELECT * FROM ingest_state WHERE source = 'flaky'").fetchone()
    assert "top-secret" not in state["last_error"] and "***" in state["last_error"]
    assert state["consecutive_failures"] == 0 and state["last_success_at"] is not None


@pytest.fixture
def legacy_dir(tmp_path):
    (tmp_path / "guardian" / "database").mkdir(parents=True)
    conn = sqlite3.connect(tmp_path / "guardian" / "database" / "guardian.db")
    conn.execute(
        "CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT, author TEXT, section TEXT,"
        " publish_date TEXT, url TEXT, word_count INTEGER, body_text TEXT, processed_status TEXT)"
    )
    conn.execute(
        "INSERT INTO articles VALUES (1, 'T', 'By X', 'US news', '2024-05-01T10:00:00Z',"
        " 'https://www.theguardian.com/us-news/2024/may/01/story', 500,"
        " 'Intro. The nuclear plant reopened. Unrelated sentence.', 'processed')"
    )
    conn.commit()
    conn.close()
    (tmp_path / "youtube").mkdir()
    with (tmp_path / "youtube" / "Youtube_Label.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "video_id",
                "title",
                "published_at",
                "channel_title",
                "view_count",
                "like_count",
                "comment_count",
                "comment_author",
                "comment_text",
                "comment_published_at",
                "comment_like_count",
                "Sentiment",
            ],
        )
        writer.writeheader()
        row = {
            "video_id": "v1",
            "title": "Nuclear 101",
            "published_at": "2020-01-01T00:00:00Z",
            "channel_title": "C",
            "view_count": "10.0",
            "like_count": "1.0",
            "comment_count": "2.0",
            "comment_author": "@a",
            "comment_text": "Loved it",
            "comment_published_at": "2023-07-30T05:47:02Z",
            "comment_like_count": "0.0",
            "Sentiment": "2",
        }
        writer.writerow(row)
        writer.writerow(row)  # The real CSV contains exact duplicates; they must collapse.
    return tmp_path


async def test_legacy_import_is_idempotent_and_dates_comments_correctly(legacy_dir, database_url, db):
    from sentiment.importer.legacy import default_paths

    paths = default_paths(legacy_dir)
    for source in ("guardian", "youtube"):
        await import_documents(database_url, documents_for(source, paths))
    again = await import_documents(database_url, documents_for("youtube", paths))
    assert again["new_documents"] == 0
    rows = db.execute(
        "SELECT platform, kind, external_id, published_at, origin, raw FROM documents ORDER BY id"
    ).fetchall()
    assert [(r["platform"], r["kind"]) for r in rows] == [
        ("guardian", "article"),
        ("youtube", "video"),
        ("youtube", "comment"),
    ]
    assert rows[0]["external_id"] == "us-news/2024/may/01/story"
    assert rows[2]["published_at"] == datetime(2023, 7, 30, 5, 47, 2, tzinfo=UTC)
    assert rows[2]["raw"] == {"true_label": 2}
    assert {r["origin"] for r in rows} == {"backfill"}
    segments = db.execute("SELECT text FROM segments ORDER BY id").fetchall()
    assert [s["text"] for s in segments] == ["The nuclear plant reopened.", "Loved it"]


def test_threads_cannot_be_imported(legacy_dir):
    from sentiment.importer.legacy import default_paths

    with pytest.raises(ValueError, match="Threads data is intentionally excluded"):
        documents_for("threads", default_paths(legacy_dir))

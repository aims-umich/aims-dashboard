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
    from sentiment.importer.legacy import default_paths, youtube_documents

    paths = default_paths(legacy_dir)
    await import_documents(database_url, documents_for("guardian", paths))
    # The CLI refuses YouTube (30-day rule); the parser itself is still exercised for correctness.
    await import_documents(database_url, youtube_documents(paths["youtube"]))
    again = await import_documents(database_url, youtube_documents(paths["youtube"]))
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


def test_threads_and_legacy_youtube_cannot_be_imported(legacy_dir):
    from sentiment.importer.legacy import default_paths

    with pytest.raises(ValueError, match="Threads data is intentionally excluded"):
        documents_for("threads", default_paths(legacy_dir))
    with pytest.raises(ValueError, match="30-day storage limit"):
        documents_for("youtube", default_paths(legacy_dir))


def test_recompute_relevance_requeues_and_excludes(db, database_url):
    from sentiment.maintenance import recompute_relevance

    doc = db.execute(
        "INSERT INTO documents (platform, external_id, kind, published_at)"
        " VALUES ('mastodon', 'x', 'post', now()) RETURNING id"
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO segments (document_id, ordinal, text, relevance, relevance_reason) VALUES"
        " (%s, 0, 'Iran nuclear talks resume', 'relevant', NULL),"
        " (%s, 1, 'A new nuclear plant opens', 'excluded', 'no_keyword')",
        (doc, doc),
    )
    assert recompute_relevance(database_url, dry_run=True)["changed"] == 2
    result = recompute_relevance(database_url)
    assert result == {"checked": 2, "changed": 2, "relevant->excluded": 1, "excluded->relevant": 1}
    assert recompute_relevance(database_url)["changed"] == 0


def test_recompute_relevance_classifies_like_the_collectors(db, database_url):
    from sentiment.maintenance import recompute_relevance

    def insert(platform, external_id, title, body, texts):
        doc = db.execute(
            "INSERT INTO documents (platform, external_id, kind, title, body, lang, published_at)"
            " VALUES (%s, %s, 'article', %s, %s, 'en', now()) RETURNING id",
            (platform, external_id, title, body),
        ).fetchone()["id"]
        for ordinal, text in enumerate(texts):
            db.execute(
                "INSERT INTO segments (document_id, ordinal, text, relevance)"
                " VALUES (%s, %s, %s, 'relevant')",
                (doc, ordinal, text),
            )

    # The NYT keyword is only in the headline, which the collector judges together with the abstract.
    insert(
        "nyt",
        "a",
        "A New Small Nuclear Reactor Is Approved",
        "Regulators signed off on Tuesday.",
        ["Regulators signed off on Tuesday."],
    )
    # A Guardian sentence is judged together with the rest of its article.
    insert(
        "guardian", "b", "Zverev clinches Laver Cup", "A tense final.", ["He hit a nuclear forehand to win."]
    )
    insert(
        "guardian", "c", "Budget passes", None, ["A new nuclear plant was funded.", "Nuclear is the future."]
    )

    assert recompute_relevance(database_url) == {"checked": 4, "changed": 1, "relevant->excluded": 1}
    reasons = db.execute(
        "SELECT text, relevance_reason FROM segments WHERE relevance = 'excluded'"
    ).fetchall()
    assert [(r["text"], r["relevance_reason"]) for r in reasons] == [
        ("He hit a nuclear forehand to win.", "off_topic_article")
    ]


def test_gpt_meta_commentary_is_stripped_from_legacy_summaries():
    from sentiment.importer.legacy import clean_gpt_summary

    assert clean_gpt_summary('The text is not related to "nuclear".') == ""
    assert (
        clean_gpt_summary(
            'The text is related to the keyword "nuclear." It discusses larger nuclear families.'
        )
        == "It discusses larger nuclear families."
    )
    assert (
        clean_gpt_summary("Summary: The text discusses a new reactor.") == "The text discusses a new reactor."
    )


def test_migrations_ship_inside_the_package(tmp_path):
    """The container installs a wheel, not a checkout, so migrations must travel with the package."""
    import subprocess
    import sys
    import zipfile
    from pathlib import Path

    backend = Path(__file__).resolve().parent.parent
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(tmp_path), str(backend)],
        check=True,
    )
    names = zipfile.ZipFile(next(tmp_path.glob("sentiment-*.whl"))).namelist()
    assert "sentiment/migrations/env.py" in names
    assert "sentiment/migrations/versions/0001_initial_schema.py" in names


def test_legacy_mastodon_reads_account_repr_with_datetimes(tmp_path):
    from sentiment.importer.legacy import mastodon_documents

    fields = [
        "label",
        "id",
        "created_at",
        "language",
        "uri",
        "url",
        "content",
        "account",
        "media_attachments",
    ]
    human = (
        "{'id': 1, 'acct': 'alice@example.social', 'bot': False, 'created_at': datetime.datetime(2022, 1, 1)}"
    )
    bot = "{'id': 2, 'acct': 'newsbot@example.social', 'bot': True, 'created_at': datetime.datetime(2022, 1)}"
    path = tmp_path / "posts.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, account in enumerate((human, bot)):
            writer.writerow(
                {
                    "label": "neutral",
                    "id": str(i),
                    "created_at": "2024-11-14 16:14:04+00:00",
                    "language": "en",
                    "uri": f"https://example.social/statuses/{i}",
                    "url": "",
                    "content": "<p>nuclear power</p>",
                    "account": account,
                    "media_attachments": "[]",
                }
            )
    docs = list(mastodon_documents([path]))
    assert [d.author_handle for d in docs] == ["alice@example.social"]

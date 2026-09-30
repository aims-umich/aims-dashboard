from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from sentiment.api.app import create_app
from sentiment.db import async_pool
from sentiment.ingest import store
from sentiment.ingest.retention import RetentionJob
from sentiment.ingest.sources.guardian import parse_result
from sentiment.scorer.service import register_model, score_batch
from tests import factories as f
from tests.fake import FakeClassifier


@pytest.fixture
async def pool(database_url, db):
    pool = await async_pool(database_url)
    yield pool
    await pool.close()


async def save_article(pool, article_id: str) -> None:
    body = "The council met. A good new nuclear plant was approved. A bad reactor outage followed."
    doc = parse_result(f.guardian_result(article_id, body, date=datetime.now(UTC).isoformat()))
    async with pool.connection() as conn, conn.transaction():
        await store.save_documents(conn, [doc])


async def test_retention_purges_text_but_keeps_scores(settings, pool, db):
    await save_article(pool, "us-news/old")
    await save_article(pool, "us-news/new")
    clf = FakeClassifier()
    model = register_model(db, clf.info)
    while score_batch(db, clf, model, 10):
        pass
    db.execute(
        "UPDATE documents SET collected_at = now() - interval '25 hours' WHERE external_id = 'us-news/old'"
    )

    settings.enabled_sources = "guardian"
    settings.text_retention_hours = "guardian=24"
    async with httpx.AsyncClient() as client:
        result = await RetentionJob(settings, client, pool).poll({})
    assert result.cursor == {"purged": {"guardian": 1}}

    old = db.execute("SELECT * FROM documents WHERE external_id = 'us-news/old'").fetchone()
    assert (old["title"], old["body"], old["url"], old["author_handle"], old["raw"]) == (
        None,
        None,
        None,
        None,
        None,
    )
    assert old["text_purged_at"] is not None
    texts = db.execute("SELECT text FROM segments WHERE document_id = %s", (old["id"],)).fetchall()
    assert texts and all(row["text"] == "" for row in texts)
    assert (
        db.execute("SELECT count(*) AS n FROM predictions").fetchone()["n"] == 4
    )  # both articles, two sentences each

    with TestClient(create_app(settings)) as api:
        summary = api.get("/api/v1/platforms/guardian/summary").json()
        assert summary["totals"]["documents"] == 2  # history keeps counting the purged article
        assert summary["sentiment"] == {"negative": 2, "neutral": 0, "positive": 2}
        posts = api.get("/api/v1/platforms/guardian/posts").json()["items"]
        assert [p["title"] for p in posts] == ["Title for us-news/new"]
        assert api.get("/api/v1/platforms/guardian/words").json()["sampled"] == 2
        assert api.get("/api/v1/status").json()["scorer"]["backlog"] == 0


async def test_purged_documents_stay_purged_when_polled_again(settings, pool, db):
    await save_article(pool, "us-news/again")
    db.execute("UPDATE documents SET collected_at = now() - interval '2 days'")
    settings.text_retention_hours = "guardian=24"
    async with httpx.AsyncClient() as client:
        await RetentionJob(settings, client, pool).poll({})
    await save_article(pool, "us-news/again")  # the collector's overlapping window returns it again
    row = db.execute("SELECT title, url, author_handle, text_purged_at FROM documents").fetchone()
    assert (row["title"], row["url"], row["author_handle"]) == (None, None, None)
    assert db.execute("SELECT count(*) AS n FROM documents").fetchone()["n"] == 1


def test_scorer_never_scores_purged_text(db):
    doc = db.execute(
        "INSERT INTO documents (platform, external_id, kind, published_at, text_purged_at)"
        " VALUES ('guardian', 'x', 'article', now(), now()) RETURNING id"
    ).fetchone()["id"]
    db.execute(
        "INSERT INTO segments (document_id, ordinal, text, relevance) VALUES (%s, 0, '', 'relevant')", (doc,)
    )
    clf = FakeClassifier()
    assert score_batch(db, clf, register_model(db, clf.info), 10) == 0


@pytest.mark.respx(assert_all_called=True)
async def test_nyt_archive_backfill_keeps_nuclear_articles_and_replaces_legacy(
    settings, db, respx_mock, monkeypatch
):
    from sentiment.maintenance import backfill_nyt

    monkeypatch.setattr("sentiment.ingest.sources.nyt.REQUEST_SPACING_S", 0)
    db.execute(
        "INSERT INTO documents (platform, external_id, kind, published_at, origin)"
        " VALUES ('nyt', 'legacy-1', 'article', now(), 'backfill')"
    )
    nuclear = f.nyt_doc("n1", "A reactor restart in Michigan.", headline="Palisades Plant Restarts")
    other = f.nyt_doc("o1", "The mayor opened a park.", headline="New Park")
    respx_mock.get("https://api.nytimes.com/svc/archive/v1/2024/12.json").respond(
        json={"response": {"docs": [nuclear, other]}}
    )
    respx_mock.get("https://api.nytimes.com/svc/archive/v1/2025/1.json").respond(
        json={"response": {"docs": []}}
    )
    totals = await backfill_nyt(settings, (2024, 12), (2025, 1), replace_legacy=True)
    assert totals == {
        "months": 2,
        "articles": 2,
        "kept": 1,
        "new_documents": 1,
        "new_segments": 1,
        "legacy_deleted": 1,
    }
    rows = db.execute("SELECT external_id, origin, title FROM documents").fetchall()
    assert rows == [
        {"external_id": "nyt://article/n1", "origin": "backfill", "title": "Palisades Plant Restarts"}
    ]


async def test_region_filter_keeps_only_us_articles(settings, pool, db):
    body = "A good new nuclear plant was approved."
    us = parse_result(f.guardian_result("us-news/a", body, date=datetime.now(UTC).isoformat()))
    uk = parse_result(
        f.guardian_result("environment/b", body, date=datetime.now(UTC).isoformat())
        | {"sectionId": "environment"}
    )
    async with pool.connection() as conn, conn.transaction():
        await store.save_documents(conn, [us, uk])
    clf = FakeClassifier()
    model = register_model(db, clf.info)
    while score_batch(db, clf, model, 10):
        pass
    settings.enabled_sources = "guardian"
    with TestClient(create_app(settings)) as api:
        everything = api.get("/api/v1/platforms/guardian/summary").json()["totals"]["documents"]
        us_only = api.get("/api/v1/platforms/guardian/summary", params={"region": "us"}).json()["totals"][
            "documents"
        ]
        posts = api.get("/api/v1/platforms/guardian/posts", params={"region": "us"}).json()["items"]
        assert (everything, us_only) == (2, 1)
        assert [p["title"] for p in posts] == ["Title for us-news/a"]
        assert api.get("/api/v1/platforms/guardian/summary", params={"region": "uk"}).status_code == 422

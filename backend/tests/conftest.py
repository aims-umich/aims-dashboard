"""Tests run against a real Postgres (the same engine as production).

Set TEST_DATABASE_URL to a disposable database; every table is truncated between tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
import pytest

from sentiment.config import Settings
from sentiment.db import connect, migrate

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres@localhost:5433/dashboard_test")


@pytest.fixture(scope="session")
def database_url() -> str:
    try:
        with psycopg.connect(TEST_DATABASE_URL, connect_timeout=3, autocommit=True) as conn:
            conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not available at TEST_DATABASE_URL: {exc}")
    migrate(TEST_DATABASE_URL)
    return TEST_DATABASE_URL


@pytest.fixture
def db(database_url: str) -> Iterator[psycopg.Connection]:
    with connect(database_url, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE documents, segments, predictions, models, ingest_state RESTART IDENTITY CASCADE"
        )
        yield conn


@pytest.fixture
def settings(database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url,
        enabled_sources="bluesky,mastodon,youtube,guardian,nyt",
        guardian_api_key="guardian-secret",
        nyt_api_key="nyt-secret",
        youtube_api_key="yt-secret",
        reddit_client_id="reddit-id",
        reddit_client_secret="reddit-secret",
        api_cache_ttl_s=0,
        log_format="text",
    )

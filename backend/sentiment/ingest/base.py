"""Shared types for collectors.

A collector ("job") turns one platform API into `DocumentIn` records.
Polling jobs implement `poll(cursor)`; streaming jobs implement `stream(...)` and manage their own loop.
Each job owns one `ingest_state` row, so one failing job never affects another.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

import httpx
from psycopg_pool import AsyncConnectionPool

from sentiment.config import Settings
from sentiment.text import Relevance


@dataclass(slots=True)
class SegmentIn:
    text: str
    relevance: Relevance


@dataclass(slots=True)
class DocumentIn:
    platform: str
    external_id: str
    kind: str
    published_at: datetime
    segments: list[SegmentIn] = field(default_factory=list)
    url: str | None = None
    author_handle: str | None = None
    title: str | None = None
    body: str | None = None
    lang: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] | None = None
    parent_external_id: str | None = None
    origin: str = "live"


@dataclass(slots=True)
class PollResult:
    documents: list[DocumentIn]
    cursor: dict[str, Any]
    fetched: int
    # Optional follow-up writes that must commit with the documents (metrics refreshes, deletions).
    metric_updates: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)
    deletions: list[tuple[str, str]] = field(default_factory=list)


class RateLimitedError(Exception):
    def __init__(self, retry_after_s: float, message: str = "rate limited") -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class SourceDisabledError(Exception):
    """Raised when a job cannot run with the current configuration (for example, a missing key)."""


class Job:
    """A polling collector. Subclasses set `name`, `platform`, and implement `poll`."""

    name: ClassVar[str]
    platform: ClassVar[str]

    def __init__(self, settings: Settings, client: httpx.AsyncClient, pool: AsyncConnectionPool) -> None:
        self.settings = settings
        self.client = client
        # For jobs that read what is already stored (metrics refreshes, compliance sweeps).
        self.pool = pool

    @property
    def interval_s(self) -> float:
        raise NotImplementedError

    def secrets(self) -> list[str]:
        """Secret values this job uses, so they can be scrubbed from error messages."""
        return []

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        raise NotImplementedError


_KEY_PARAMS = re.compile(r"((?:api[-_]?key|key|access_token|token|client_secret)=)[^&\s'\"]+", re.IGNORECASE)


def redact(message: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, "***")
    return _KEY_PARAMS.sub(r"\1***", message)[:2000]


def raise_for_status(response: httpx.Response) -> None:
    """Map HTTP errors onto retry behaviour without leaking request URLs (which may hold keys)."""
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after", "")
        wait = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else 900.0
        raise RateLimitedError(wait, f"HTTP 429 from {response.url.host}")
    if response.status_code >= 400:
        detail = response.text[:300].replace("\n", " ")
        raise httpx.HTTPStatusError(
            f"HTTP {response.status_code} from {response.url.host}{response.url.path}: {detail}",
            request=response.request,
            response=response,
        )

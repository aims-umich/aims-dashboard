"""The public read API. Stateless and read-only: it never collects data or loads a model."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from sentiment.api import queries
from sentiment.api.platforms import PLATFORMS, Platform, enabled_platforms
from sentiment.config import Settings, get_settings
from sentiment.ingest.sources import JOBS_BY_SOURCE

log = logging.getLogger(__name__)

STALE_AFTER_INTERVALS = 3
FAILING_AFTER = 3  # consecutive failed runs before a job counts as broken, however recent its last success
SEVERITY = {"ok": 0, "pending": 1, "stale": 2, "error": 3}
RangeParam = Annotated[str, Query(pattern="^(7d|30d|90d|1y|all)$")]
# "us" keeps only items the source itself classifies as about the United States (Guardian tags).
RegionParam = Annotated[str | None, Query(pattern="^(us)$")]


class TTLCache:
    """A tiny per-process response cache; every viewer polls the same few URLs every 60 s."""

    def __init__(self, ttl_s: float) -> None:
        self.ttl_s = ttl_s
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: str, compute: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
            if hit and now - hit[0] < self.ttl_s:
                return hit[1]
        value = compute()
        with self._lock:
            self._items[key] = (now, value)
            if len(self._items) > 2000:
                cutoff = now - self.ttl_s
                self._items = {k: v for k, v in self._items.items() if v[0] >= cutoff}
        return value


class RateLimiter:
    """Sliding-window limit per client IP, as a basic guard for a public, unauthenticated API."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            if len(self._hits) > 10_000:
                self._hits = defaultdict(deque, {k: v for k, v in self._hits.items() if v})
            return True


def client_ip(request: Request) -> str:
    # Caddy appends the connecting address to X-Forwarded-For; Vercel's proxy puts the viewer first.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def job_names(source: str) -> list[str]:
    return [job.name for job in JOBS_BY_SOURCE.get(source, [])]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    cache = TTLCache(settings.api_cache_ttl_s)
    limiter = RateLimiter(settings.api_rate_limit_per_min)
    state: dict[str, ConnectionPool] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        state["pool"] = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={
                "row_factory": dict_row,
                "autocommit": True,
                # Defense in depth: this service can only read, and no query can run away.
                "options": "-c default_transaction_read_only=on -c statement_timeout=10000 -c TimeZone=UTC",
            },
            open=True,
        )
        yield
        state["pool"].close()

    app = FastAPI(
        title="AIMS Nuclear Sentiment API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=["*"]
    )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.url.path.startswith("/api/") and not limiter.allow(client_ip(request)):
            return JSONResponse(
                {"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"}
            )
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/"):
            # Let Vercel's edge and browsers reuse responses briefly, so load on the VM stays flat.
            ttl = int(settings.api_cache_ttl_s)
            response.headers.setdefault(
                "Cache-Control", f"public, max-age={ttl}, s-maxage={ttl}, stale-while-revalidate={ttl * 2}"
            )
        return response

    @contextmanager
    def db() -> Iterator[psycopg.Connection]:
        try:
            with state["pool"].connection(timeout=10) as conn:
                yield conn
        except psycopg.OperationalError as exc:
            log.error("database unavailable", extra={"error": str(exc)})
            raise HTTPException(503, "Database unavailable") from exc

    def platform_or_404(key: str) -> Platform:
        platform = PLATFORMS.get(key)
        if platform is None or platform not in enabled_platforms(settings):
            raise HTTPException(404, f"Unknown platform: {key}")
        return platform

    def build_status() -> dict[str, Any]:
        now = datetime.now(UTC)
        with db() as conn:
            states = queries.ingest_states(conn)
            scorer = queries.scorer_status(conn)
        platforms = []
        for platform in enabled_platforms(settings):
            jobs = []
            for name in job_names(platform.key):
                row = states.get(name)
                if row is None:
                    jobs.append({"job": name, "state": "pending", "last_success_at": None})
                    continue
                interval = timedelta(seconds=row["interval_s"] or 3600)
                last_ok = row["last_success_at"]
                if row["consecutive_failures"] >= FAILING_AFTER:
                    job_state = "error"
                elif last_ok and now - last_ok <= interval * STALE_AFTER_INTERVALS:
                    job_state = "ok"
                elif last_ok is None and row["consecutive_failures"] == 0:
                    job_state = "pending"
                else:
                    job_state = "stale" if row["consecutive_failures"] == 0 else "error"
                jobs.append(
                    {
                        "job": name,
                        "state": job_state,
                        "interval_s": row["interval_s"],
                        "last_success_at": last_ok,
                        "last_error_at": row["last_error_at"],
                        "consecutive_failures": row["consecutive_failures"],
                        "items_last_run": row["items_last_run"],
                        "new_last_run": row["new_last_run"],
                    }
                )
            primary = jobs[0] if jobs else {"state": "pending", "last_success_at": None}
            # A platform is only as healthy as its least healthy job (YouTube needs search and comments).
            worst = max((job["state"] for job in jobs), key=SEVERITY.__getitem__, default="pending")
            platforms.append(
                {
                    "platform": platform.key,
                    "name": platform.name,
                    "state": worst,
                    "last_success_at": primary["last_success_at"],
                    "jobs": jobs,
                }
            )
        last_scored = scorer["last_scored_at"]
        scorer_ok = scorer["model"] is not None and (
            scorer["backlog"] == 0 or (last_scored is not None and now - last_scored < timedelta(minutes=10))
        )
        return {"generated_at": now, "platforms": platforms, "scorer": scorer | {"ok": scorer_ok}}

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, Any]:
        with db() as conn:
            conn.execute("SELECT 1")
        return {"ok": True}

    @app.get("/api/v1/status")
    def status() -> dict[str, Any]:
        return cache.get_or_set("status", build_status)

    @app.get("/api/v1/platforms")
    def platforms(range: RangeParam = "30d") -> dict[str, Any]:
        def compute() -> dict[str, Any]:
            status_by_platform = {p["platform"]: p for p in build_status()["platforms"]}
            items = []
            with db() as conn:
                for platform in enabled_platforms(settings):
                    summary = queries.summary(conn, platform, range)
                    items.append(
                        {
                            "platform": platform.key,
                            "name": platform.name,
                            "unit": platform.unit,
                            "totals": summary["totals"],
                            "scored_all_time": queries.scored_count(conn, platform),
                            "sentiment": summary["sentiment"],
                            "net_sentiment": summary["net_sentiment"],
                            "status": status_by_platform[platform.key]["state"],
                            "last_success_at": status_by_platform[platform.key]["last_success_at"],
                        }
                    )
            return {"range": range, "platforms": items}

        return cache.get_or_set(f"platforms:{range}", compute)

    @app.get("/api/v1/platforms/{key}/summary")
    def summary(key: str, range: RangeParam = "all", region: RegionParam = None) -> dict[str, Any]:
        platform = platform_or_404(key)
        us = region == "us"

        def compute() -> dict[str, Any]:
            with db() as conn:
                return queries.summary(conn, platform, range, us) | {
                    "name": platform.name,
                    "unit": platform.unit,
                }

        return cache.get_or_set(f"summary:{key}:{range}:{region}", compute)

    @app.get("/api/v1/platforms/{key}/words")
    def words(key: str, range: RangeParam = "all", region: RegionParam = None) -> dict[str, Any]:
        platform = platform_or_404(key)

        def compute() -> dict[str, Any]:
            with db() as conn:
                return queries.words(conn, platform, range, us_only=region == "us")

        return cache.get_or_set(f"words:{key}:{range}:{region}", compute)

    @app.get("/api/v1/platforms/{key}/posts")
    def posts(
        key: str,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        before: Annotated[str | None, Query(max_length=64)] = None,
        sentiment: Annotated[str | None, Query(pattern="^(negative|neutral|positive)$")] = None,
        region: RegionParam = None,
    ) -> dict[str, Any]:
        platform = platform_or_404(key)
        cursor = None
        if before:
            try:
                stamp, _, doc_id = before.rpartition("_")
                cursor = (datetime.fromisoformat(stamp), int(doc_id))
            except ValueError as exc:
                raise HTTPException(400, "Invalid cursor") from exc

        def compute() -> dict[str, Any]:
            with db() as conn:
                return queries.posts(
                    conn, platform, limit=limit, before=cursor, sentiment=sentiment, us_only=region == "us"
                )

        return cache.get_or_set(f"posts:{key}:{limit}:{before}:{sentiment}:{region}", compute)

    return app


def main(settings: Settings) -> None:
    import uvicorn

    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",  # noqa: S104 - bound inside the container; only Caddy is exposed
        port=8000,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=False,
    )

"""The ingest service: one asyncio task per collector job, all isolated from each other."""

from __future__ import annotations

import asyncio
import logging
import random
import signal
from collections.abc import Awaitable, Callable

import httpx
from psycopg_pool import AsyncConnectionPool

from sentiment.config import Settings
from sentiment.db import async_pool
from sentiment.ingest import store
from sentiment.ingest.base import Job, PollResult, RateLimitedError, SourceDisabledError, redact
from sentiment.observability import Heartbeat

log = logging.getLogger(__name__)

FAIL_ALERT_AFTER = 3


def build_jobs(settings: Settings, client: httpx.AsyncClient, pool: AsyncConnectionPool) -> list[Job]:
    from sentiment.ingest.retention import RetentionJob
    from sentiment.ingest.sources import JOBS_BY_SOURCE

    # Retention always runs: it enforces the platforms' storage terms even for disabled sources.
    jobs: list[Job] = [RetentionJob(settings, client, pool)]
    for source in settings.sources:
        jobs.extend(job_cls(settings, client, pool) for job_cls in JOBS_BY_SOURCE[source])
    return jobs


class Runner:
    def __init__(self, settings: Settings, pool: AsyncConnectionPool, jobs: list[Job]) -> None:
        self.settings = settings
        self.pool = pool
        self.jobs = jobs
        self.stopping = asyncio.Event()

    async def sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self.stopping.wait(), timeout=max(0.0, seconds))
        except TimeoutError:
            pass

    async def commit(self, job: Job, result: PollResult) -> store.SaveResult:
        async with self.pool.connection() as conn:
            saved = await store.commit_run(conn, job.name, result, job.interval_s)
        if result.fetched or saved.new_documents or saved.deleted:
            log.info(
                "run committed",
                extra={
                    "job": job.name,
                    "fetched": result.fetched,
                    "new_documents": saved.new_documents,
                    "new_segments": saved.new_segments,
                    "updated_metrics": saved.updated_metrics,
                    "deleted": saved.deleted,
                },
            )
        return saved

    async def record_failure(self, job: Job, exc: BaseException) -> int:
        message = redact(f"{type(exc).__name__}: {exc}", job.secrets())
        try:
            async with self.pool.connection() as conn:
                return await store.record_failure(conn, job.name, message, job.interval_s)
        except Exception:
            log.exception("could not record failure", extra={"job": job.name})
            return 1

    async def run_job(self, job: Job) -> None:
        heartbeat = Heartbeat(self.settings, job.name)
        stream: Callable[..., Awaitable[None]] | None = getattr(job, "stream", None)
        # Stagger start-up so every job does not hit the network in the same second.
        await self.sleep(random.uniform(0, 5))
        while not self.stopping.is_set():
            try:
                async with self.pool.connection() as conn:
                    cursor = await store.load_cursor(conn, job.name)
                if stream is not None:
                    await stream(cursor, lambda result: self.commit(job, result), heartbeat, self.stopping)
                    delay = 1.0
                else:
                    await self.commit(job, await job.poll(cursor))
                    await heartbeat.ping()
                    delay = job.interval_s
            except asyncio.CancelledError:
                raise
            except SourceDisabledError as exc:
                log.warning("job disabled", extra={"job": job.name, "reason": str(exc)})
                await self.record_failure(job, exc)
                delay = 3600
            except RateLimitedError as exc:
                log.warning("rate limited", extra={"job": job.name, "retry_after_s": exc.retry_after_s})
                await self.record_failure(job, exc)
                delay = max(exc.retry_after_s, job.interval_s)
            except Exception as exc:
                failures = await self.record_failure(job, exc)
                log.error(
                    "job failed",
                    extra={"job": job.name, "failures": failures, "error": redact(str(exc), job.secrets())},
                )
                if failures == FAIL_ALERT_AFTER:
                    await heartbeat.ping(failed=True, message=redact(str(exc), job.secrets()))
                delay = min(job.interval_s, 15 * 2 ** min(failures, 8))
            # Jitter keeps polls from synchronising with each other or with other clients.
            await self.sleep(delay * random.uniform(0.9, 1.1))

    async def run(self) -> None:
        log.info("ingest starting", extra={"jobs": [job.name for job in self.jobs]})
        tasks = [asyncio.create_task(self.run_job(job), name=job.name) for job in self.jobs]
        await self.stopping.wait()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def amain(settings: Settings) -> None:
    pool = await async_pool(settings.database_url, max_size=max(4, len(settings.sources) * 2))
    headers = {"User-Agent": settings.user_agent}
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        runner = Runner(settings, pool, build_jobs(settings, client, pool))
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, runner.stopping.set)
        try:
            await runner.run()
        finally:
            await pool.close()
    log.info("ingest stopped")


def main(settings: Settings) -> None:
    asyncio.run(amain(settings))

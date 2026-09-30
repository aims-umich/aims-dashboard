"""Text retention: after each platform's window, keep only what its terms allow.

A purged document keeps its platform, id, kind, dates, and sentiment scores, so every chart keeps its
full history. Its title, text, author, link, raw payload, and segment text are cleared. The id stays so
that a later poll of the same item is still recognized as a duplicate instead of being stored again.
"""

from __future__ import annotations

from typing import Any, ClassVar

from sentiment.ingest.base import Job, PollResult

PURGE_SQL = """
    WITH expired AS (
        SELECT id FROM documents
        WHERE platform = %(platform)s AND text_purged_at IS NULL
          AND collected_at < now() - make_interval(secs => %(seconds)s)
        ORDER BY collected_at
        LIMIT %(limit)s
        FOR UPDATE SKIP LOCKED
    ),
    cleared_segments AS (
        UPDATE segments SET text = '' FROM expired WHERE segments.document_id = expired.id
        RETURNING segments.id
    )
    UPDATE documents d
    SET title = NULL, body = NULL, author_handle = NULL, url = NULL, raw = NULL, text_purged_at = now()
    FROM expired WHERE d.id = expired.id
    RETURNING d.id, (SELECT count(*) FROM cleared_segments) AS segments
"""


class RetentionJob(Job):
    name: ClassVar[str] = "retention"
    platform: ClassVar[str] = "system"
    BATCH = 5000

    @property
    def interval_s(self) -> float:
        return self.settings.retention_interval_s

    async def purge(self, platform: str, hours: float) -> int:
        total = 0
        while True:
            async with self.pool.connection() as conn, conn.transaction():
                rows = await (
                    await conn.execute(
                        PURGE_SQL, {"platform": platform, "seconds": hours * 3600, "limit": self.BATCH}
                    )
                ).fetchall()
            total += len(rows)
            if len(rows) < self.BATCH:
                return total

    async def poll(self, cursor: dict[str, Any]) -> PollResult:
        purged = {
            platform: await self.purge(platform, hours)
            for platform, hours in self.settings.retention_hours.items()
        }
        return PollResult(documents=[], cursor={"purged": purged}, fetched=sum(purged.values()))

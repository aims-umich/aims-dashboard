"""Operational jobs run by hand from the CLI."""

from __future__ import annotations

from collections import Counter

from sentiment.db import NEW_SEGMENTS_CHANNEL, connect
from sentiment.text import classify_relevance


def recompute_relevance(database_url: str, *, dry_run: bool = False) -> dict[str, int]:
    """Re-apply the current relevance rules to every stored segment.

    Run this after changing the rules in `sentiment.text`. Segments that become relevant are queued for
    scoring automatically; segments that become excluded simply stop counting (their scores are kept).
    """
    changes: Counter[str] = Counter()
    with connect(database_url) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.text, s.relevance, s.relevance_reason, d.lang, d.kind
            FROM segments s JOIN documents d ON d.id = s.document_id
            """
        ).fetchall()
        updates = []
        for row in rows:
            result = classify_relevance(
                row["text"], lang=row["lang"], context_relevant=row["kind"] == "comment"
            )
            if (result.status, result.reason) != (row["relevance"], row["relevance_reason"]):
                changes[f"{row['relevance']}->{result.status}"] += 1
                updates.append((result.status, result.reason, row["id"]))
        if updates and not dry_run:
            with conn.transaction(), conn.cursor() as cur:
                cur.executemany(
                    "UPDATE segments SET relevance = %s, relevance_reason = %s WHERE id = %s", updates
                )
                cur.execute(f"NOTIFY {NEW_SEGMENTS_CHANNEL}")
    return {"checked": len(rows), "changed": sum(changes.values()), **changes}

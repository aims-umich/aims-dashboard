"""Command line entry point: `sentiment <command>` (also `python -m sentiment`)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sentiment.config import get_settings
from sentiment.db import BACKEND_DIR, connect, migrate
from sentiment.observability import setup


def cmd_migrate(_: argparse.Namespace) -> None:
    migrate(get_settings().database_url)


def cmd_ingest(_: argparse.Namespace) -> None:
    from sentiment.ingest.runner import main

    main(get_settings())


def cmd_scorer(_: argparse.Namespace) -> None:
    from sentiment.scorer.service import main

    main(get_settings())


def cmd_api(_: argparse.Namespace) -> None:
    from sentiment.api.app import main

    main(get_settings())


def cmd_import_legacy(args: argparse.Namespace) -> None:
    from sentiment.importer.legacy import default_paths, documents_for, import_documents

    paths = default_paths(Path(args.backend_dir))
    for source in args.sources:
        totals = asyncio.run(import_documents(get_settings().database_url, documents_for(source, paths)))
        print(json.dumps({"source": source, **totals}))


def cmd_relevance(args: argparse.Namespace) -> None:
    from sentiment.maintenance import recompute_relevance

    print(json.dumps(recompute_relevance(get_settings().database_url, dry_run=args.dry_run)))


def cmd_seed_demo(_: argparse.Namespace) -> None:
    from sentiment.maintenance import seed_demo

    settings = get_settings()
    if settings.environment == "production":
        sys.exit("Refusing to seed demo data into a production database.")
    print(json.dumps(seed_demo(settings.database_url, settings.sources)))


def _month(value: str) -> tuple[int, int]:
    year, _, month = value.partition("-")
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        raise argparse.ArgumentTypeError("use YYYY-MM")
    return int(year), int(month)


def cmd_backfill_nyt(args: argparse.Namespace) -> None:
    from sentiment.maintenance import backfill_nyt

    totals = asyncio.run(
        backfill_nyt(get_settings(), args.start, args.end, replace_legacy=args.replace_legacy)
    )
    print(json.dumps(totals))


def cmd_models(args: argparse.Namespace) -> None:
    with connect(get_settings().database_url) as conn:
        if args.action == "activate":
            with conn.transaction():
                row = conn.execute(
                    "SELECT id FROM models WHERE name = %s AND (%s::text IS NULL OR revision = %s)"
                    " ORDER BY created_at DESC LIMIT 1",
                    (args.name, args.revision, args.revision),
                ).fetchone()
                if row is None:
                    sys.exit(f"No registered model named {args.name!r}; start its scorer first.")
                conn.execute("UPDATE models SET is_active = false WHERE is_active")
                conn.execute("UPDATE models SET is_active = true WHERE id = %s", (row["id"],))
        rows = conn.execute(
            """
            SELECT m.id, m.name, m.revision, m.backend, m.is_active,
                   (SELECT count(*) FROM predictions p WHERE p.model_id = m.id) AS predictions
            FROM models m ORDER BY m.id
            """
        ).fetchall()
    for row in rows:
        print(json.dumps(row, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentiment", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations").set_defaults(func=cmd_migrate)
    sub.add_parser("ingest", help="run the collectors").set_defaults(func=cmd_ingest)
    sub.add_parser("scorer", help="run the sentiment scorer").set_defaults(func=cmd_scorer)
    sub.add_parser("api", help="serve the read API on :8000").set_defaults(func=cmd_api)

    legacy = sub.add_parser("import-legacy", help="import the pre-2026 SQLite/CSV data")
    legacy.add_argument("sources", nargs="+", choices=["guardian", "mastodon", "nyt"])
    legacy.add_argument(
        "--backend-dir", default=str(BACKEND_DIR), help="folder holding the old collector data"
    )
    legacy.set_defaults(func=cmd_import_legacy)

    relevance = sub.add_parser("relevance", help="re-apply the relevance rules to stored segments")
    relevance.add_argument("--dry-run", action="store_true", help="only report what would change")
    relevance.set_defaults(func=cmd_relevance)

    nyt = sub.add_parser("backfill-nyt", help="rebuild NYT history from the Archive API")
    nyt.add_argument("--from", dest="start", type=_month, required=True, metavar="YYYY-MM")
    nyt.add_argument("--to", dest="end", type=_month, required=True, metavar="YYYY-MM")
    nyt.add_argument(
        "--replace-legacy", action="store_true", help="then delete the old GPT-written NYT summaries"
    )
    nyt.set_defaults(func=cmd_backfill_nyt)

    sub.add_parser("seed-demo", help="fill a dev/CI database with fake data").set_defaults(func=cmd_seed_demo)

    models = sub.add_parser("models", help="list models, or choose which one the dashboard shows")
    models.add_argument("action", choices=["list", "activate"])
    models.add_argument("name", nargs="?")
    models.add_argument("revision", nargs="?")
    models.set_defaults(func=cmd_models)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "models" and args.action == "activate" and not args.name:
        sys.exit("usage: sentiment models activate NAME [REVISION]")
    setup(get_settings(), args.command)
    args.func(args)


if __name__ == "__main__":
    main()

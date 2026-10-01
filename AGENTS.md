# dashboard (Nuclear Energy Sentiment Dashboard)

Canonical entry document for this project.
`CLAUDE.md` delegates here, so read this first.

## Shared Memory Workspace

Use `../../wiki/index.md` as shared long-term memory when relevant; follow only relevant links and its write workflow for durable facts, decisions, and relationships. This project's files remain authoritative for current project state.

## What this is

A live dashboard of public sentiment toward nuclear energy across social media and news, for the AIMS Lab.
It began as a UROP Symposium demo (tagged `v0-local-demo`) and was rebuilt in September 2026 as a live service at `dashboard.aims-umich.com`.

- Remote: `git@github.com:jere67/aims-dashboard.git`, which redirects to `aims-umich/aims-dashboard` (public). Branch `main`.
- Frontend on Vercel Hobby; backend on an Oracle Cloud Always Free arm64 VM; everything on free tiers.

## Layout

- `backend/` - Python 3.12 package `sentiment` (CLI: `sentiment <command>`).
  - `ingest/` - collectors, one isolated job per feed (`sources/`: bluesky, mastodon, youtube, reddit, guardian, nyt), idempotent upserts, cursors in `ingest_state`.
  - `scorer/` - loads one `Classifier` (`classifier/`), claims unscored segments with `SKIP LOCKED`, wakes on `LISTEN/NOTIFY new_segments`. When the queue is empty it explains recent posts and comments (integrated gradients, `explanations` table).
  - `api/` - read-only FastAPI (`/api/v1/...`, `/healthz`).
  - `text.py` - cleanup, sentence splitting, language checks, and the nuclear-energy relevance rules (Guardian sentences are judged with their article's context).
  - `topics.py` - keyword rules for the nine topics, stored per segment in `segments.topics`.
  - `events.py` - the lab's fixed list of events for the Events page; spikes are detected in `api/queries.py`.
  - `importer/legacy.py` - one-time import of the old SQLite/CSV data.
  - `migrations/` - Alembic migrations (inside the package), written as raw SQL.
  - `tests/` - pytest against a real Postgres (`TEST_DATABASE_URL`).
- `frontend/` - React 19 + Vite + Tailwind 4. Design tokens (both themes) are in `src/index.css`; charts are plain SVG and HTML in `src/components/charts/`. `src/pages/SourcePage.jsx` is one data-driven page for every platform, configured in `src/lib/platforms.js`; Compare, Topics, Events, and Model have their own pages. Playwright E2E is in `e2e/`.
- `compose.yaml` - Postgres, migrate, ingest, scorer, api, and Caddy (profile `public`).
- `deploy/` - VM bootstrap, deploy, backup, and restore scripts, the Caddyfile, `env.example`, and the operations runbook (`deploy/README.md`).
- `.github/workflows/` - CI on pull requests; deploy on `main` (arm64 images to GHCR, then SSH to the VM).

## Data model

`documents` (unique on `platform, external_id`) → `segments` (scorable spans with a `relevance` status and reason, and `topics`) → `predictions` (keyed by `segment_id, model_id`, with all three probabilities) and `explanations` (the words that pushed each prediction, as character spans).
The dashboard shows only `relevance = 'relevant'` segments scored by the one `models.is_active` model.
Canonical labels are `0 = negative, 1 = neutral, 2 = positive`, converted only at the classifier boundary.

## Run and test

See `README.md` for commands.
In short: `sentiment migrate`, then `sentiment seed-demo` (or the real `ingest` and `scorer`), then `sentiment api` and `npm run dev` in `frontend/` (Vite proxies `/api` to `127.0.0.1:8000`).
Checks: `ruff check . && ruff format --check . && pytest` in `backend/`; `npm run lint && npm run build` and `npx playwright test` in `frontend/`.

## Rules and gotchas

- **Official APIs only, within each platform's terms.** No scraping. Threads and X are out of scope.
  YouTube data must be refreshed or deleted within 30 days (Developer Policies III.E.4); `youtube_refresh` does both, and YouTube is shown only as topic-level aggregates, never per-channel scores. Old YouTube data without comment ids cannot be refreshed, so it is not imported.
  `TEXT_RETENTION_HOURS` (empty by default) can purge a platform's text after a window, keeping only scores and dates.
  Mastodon `noindex` and bot accounts, and Bluesky accounts labeled `!no-unauthenticated`, are never shown.
  The old Playwright Threads scraper and its data (`backend/threads/*`, `backend/posts.db`) violated Meta's terms: never import, display, or publish them.
  `posts.db` was committed to the public repo before September 2026 and is still in git history.
- Collected data never goes in git: it lives in Postgres and in encrypted backups. The old collector folders under `backend/` only hold untracked local legacy data.
- Store only what is displayed or analyzed. Honor deletions: the Bluesky stream deletes and the Reddit compliance job both remove content deleted at the source.
- After changing relevance rules in `text.py`, run `sentiment relevance` to re-apply them to stored segments, and add test cases for both the leak and the non-leak.
- After changing topic rules in `topics.py`, run `sentiment topics`. Rules are plain keywords on purpose, so anyone can check why a text landed in a topic.
- Green, gray, and red are reserved for positive, neutral, and negative; Cherenkov blue (`--glow`) is for live status and navigation only. Headlines name the chart; text only explains how to read it, never what to conclude.
- Below 30 texts, show "too few to call" instead of a net sentiment, and hatch time before a source started collecting.
- Secrets live only in `.env` (mode 600) on the VM and in GitHub environment secrets. Collector errors pass through `redact()` before they are stored or logged.
- Every source is independent: a missing key marks that job "paused" and never blocks the others.
- The API is read-only at the connection level (`default_transaction_read_only`), so do not add write endpoints to it.
- The scorer image bakes in the model at a pinned revision (`SCORER_REVISION`). Change the model by registering a new one and shadow-scoring, never by overwriting predictions.
- Pinned Python versions are in `backend/constraints.txt`. Refresh it deliberately, never ad hoc.

## Inherited guidelines

Jeremy's global guidelines apply: no em dash (use a plain dash), never auto-add an agent as commit co-author, reproduce bugs end-to-end before fixing, and fix lint or test issues you notice along the way.
Be obsessed with pixel-perfect UI: if something looks off, even if unrelated to the current task, get it fixed along the way.
Prefer quality, simplicity, and long-term maintainability over minimizing development cost.

# Phase 1 verification

All data in automated tests is synthetic. Never point tests or browser scenarios at production. Default pytest creates a temporary SQLite database; application DATABASE_URL is overridden before importing the app. Real PostgreSQL tests use TEST_POSTGRES_URL and isolated random schemas. The public schema of this database must be empty.

## Backend

```sh
cd apps/api
.venv/bin/python -m pytest -q
TEST_POSTGRES_URL=postgresql+psycopg://TEST_USER:TEST_PASSWORD@localhost:55439/phase1_concurrency .venv/bin/python -m pytest -q
```

Without TEST_POSTGRES_URL, PostgreSQL concurrency scenarios are explicitly skipped. SQLite passes do not assert concurrency safety. Tests cover scheduling validation, provider working schedule/compatibility, closures, overlap, duration, cancellation slot release, reschedule conflicts, transition history, DST invalid/explicit times, clinic timezone and overnight intervals; authenticated tenant/role boundaries; every Retell function, signatures, confirmation, privacy fallback, persistent idempotency, write conflict rollback; call event deduplication/order and callback requests. Backend temporary-failure tests simulate an unavailable database; they do not establish network SLA behavior.

PostgreSQL concurrency tests use two simultaneous independent sessions with a barrier. Both shared-service and direct ORM insert paths are exercised. For one provider exactly one commit succeeds; different providers both succeed. Concurrent reschedules have one winner, concurrent duplicate events yield one stored event, and simultaneous identical Retell booking retries return the same committed appointment. Migrations run against each fresh test schema. These are real PostgreSQL results, not mocks. A previous experiment with a populated public schema demonstrated search-path fallback; the fixture now rejects that configuration.

## Browser

```sh
cd apps/web
npm ci
npx playwright install chromium
E2E_WEB_URL=http://localhost:33001 E2E_PASSWORD=YOUR_SYNTHETIC_PASSWORD npm run test:e2e
# Optionally use an installed local Chrome:
E2E_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Start the repeatable disposable stack from the repository root with `docker compose -f compose.test.yaml up --build -d --wait`. Its PostgreSQL data lives in tmpfs and is intentionally test-only. After testing stop it with `docker compose -f compose.test.yaml down`; it never mounts production volumes.

The suite expects this isolated stack: web at localhost:33001, API compiled into the bundle at localhost:58001, seeded synthetic admin `admin@harbordentaldemo.local`, and an unused test-date slot on 2026-11-10. The default browser test password is synthetic and must never be used for production. It tests login, backend availability selection, booking, board/history, cancellation, call section and no-token redirect. The browser plugin's node execution tool was unavailable, so local headless Chrome is the fallback. Tests create/cancel synthetic appointments; use a fresh disposable database when rerunning.

## Build and runtime

```sh
cd apps/web
npm run build
# repository root:
docker build -t avadental-api:phase1-test apps/api
docker build --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:58001 -t avadental-web:phase1-test apps/web
docker compose -f compose.prod.yaml config --quiet
```

Builds do not imply live acceptance. Container readiness requires real PostgreSQL/Redis; worker heartbeat verifies the persistent worker process. A manual test agent and phone transfer configuration are still required. See [Retell guide](../api/RETELL_FUNCTIONS.md) and [report](../architecture/phase1-implementation-report.md) for actual run results and pending checks.

# Phase 2 deployment notes

No production deployment or data migration was performed. Existing Docker/Compose/Hostinger/Coolify architecture is retained. ReportLab is the only new backend runtime dependency; bundled Vera font provides a reliable PDF fallback without fetching assets. Additional language coverage such as CJK/complex-script shaping requires suitable licensed fonts and separate rendering validation.

## Isolated local Docker verification

From the repository root:

```sh
docker compose -f compose.test.yaml up --build -d --wait
cd apps/web
E2E_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Open http://localhost:3000 (also available at http://localhost:33001); API readiness is http://localhost:58001/api/v1/health/ready and docs are http://localhost:58001/docs. The explicitly synthetic login is admin@harbordentaldemo.local / Phase1Synthetic123! from compose.test.yaml. The test stack also starts the existing worker with sandbox preparation enabled to verify heartbeat/job integration. PostgreSQL in this test stack uses tmpfs, separate credentials and a separate Compose project; stopping/removing it loses synthetic test data. Never aim browser mutation tests at a real clinic.

For source checks:

```sh
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
cd ../web
npm ci
npm run build
```

PostgreSQL integration tests require TEST_POSTGRES_URL pointing at an EMPTY disposable database with test/concurrency in its name. They create/drop random schemas and refuse application tables in public. Example used locally:

```sh
cd apps/api
TEST_POSTGRES_URL=postgresql+psycopg://postgres:phase1-test-only@127.0.0.1:55439/phase1_concurrency .venv/bin/python -m pytest -q
```

This URL is a disposable local test service, not application configuration. Without it, PostgreSQL-specific tests explicitly skip.

## Future Coolify rollout

Use the existing deployment guide `docs/deployment/COOLIFY_HOSTINGER.md`. Build API/worker from apps/api and web from apps/web; set NEXT_PUBLIC_API_BASE_URL at web build time. Retain existing DB/Redis/JWT/Retell/origin configuration, strict authentication and disabled demo seeding. `compose.prod.yaml` passes SANDBOX_REMINDERS_ENABLED (false by default) to API/worker. Setting true enables preparation only, with zero communication transport. Worker depends on healthy migrated API and retains Redis heartbeat.

Before any production rollout: resolve inherited release blockers, back up the database, rehearse this exact release on a restored anonymized Phase 1 database, inspect migration head and apply `alembic upgrade head` once before worker traffic. The checked-in API command already performs upgrade before gunicorn. Revisions A/B/C are additive; none reset databases. Downgrade is intentionally refused to protect history. On a rollback, keep added schema/data and roll back application images only after checking old-code compatibility; use a reviewed forward fix for schema changes.

After deployment separately verify strict auth, same-clinic roles, policy configuration, synthetic estimate/PDF and worker heartbeat. Configure real clinic currency/taxes/discounts/terms and clinically approved recall rules through authorized UI; no commercial or clinical defaults are silently seeded. Production e-signatures, message delivery, billing, live Retell acceptance and identity verification remain separate work.

## Native development login (port 3000)

The native FastAPI traceback `failed to resolve host 'postgres'` means Docker-only configuration was used outside Docker. Native defaults now use dedicated PostgreSQL at 127.0.0.1:55432 and Redis at 127.0.0.1:56379. `compose.local.yaml` starts only those dependencies in the avadental-local project, with a persistent dedicated database volume. Existing databases belonging to other projects are unchanged. Docker deployment configurations continue to override these defaults with their internal service URLs.

```sh
docker compose -f compose.local.yaml up -d --wait
cd apps/api
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload --port 8000
```

In another terminal, run `cd apps/web && npm run dev`. Open http://localhost:3000/login and use admin@harbordentaldemo.local / AdminPass123! for the native demo database. Native frontend defaults to API http://localhost:8000. If local environment files override DATABASE_URL/REDIS_URL with Docker-only hosts, set the corresponding native URLs explicitly; do not point at unrelated project databases. No existing account password was reset.

The separate isolated test app remains at http://localhost:33001 with API port 58001 and password Phase1Synthetic123!. Its temporary port-3000 mapping was removed because it conflicted with native Next.js. These are distinct environments and distinct databases. Earlier port-3000 checks tested the Docker app; the native traceback exposed the separate hostname problem and was subsequently verified against native port 8000.

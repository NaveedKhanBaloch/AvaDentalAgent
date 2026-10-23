# Hostinger VPS + Coolify: Phase 1 deployment preparation

No production deployment was performed. Preserve the existing PostgreSQL and Redis volumes and proxy routing. Build/test results and release blockers are listed in [the implementation report](../architecture/phase1-implementation-report.md).

## Private configuration

Use Coolify's private environment settings, never Git or frontend variables. Required values: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL, REDIS_URL, JWT_SECRET_KEY (random, at least 32 characters), RETELL_API_KEY (webhook-badged API key), ALLOWED_ORIGINS (exact HTTPS frontend origin), and NEXT_PUBLIC_API_BASE_URL (HTTPS API origin). Set RETELL_FUNCTION_RATE_LIMIT if the default 120 authenticated requests per clinic/call/minute is unsuitable.

Production Compose enforces APP_ENV=production, STRICT_AUTH_MODE=true, DEMO_SEED_ENABLED=false. No local demo-clinic fallback or login-time demo user provisioning is permitted in production. Existing users/memberships must be provisioned through the organization's approved administrative process. The change-password endpoint remains a legacy stub and must not be treated as an actual credential recovery workflow.

JWT_SECRET_KEY signs sessions; SECRET_KEY is not a substitute. RETELL_WEBHOOK_SECRET is legacy and unused: Retell verification uses RETELL_API_KEY and exact raw bytes. RETELL_AGENT_ID alone does not establish clinic routing; enable the trusted RetellIntegration row with the correct agent/clinic/tenant mapping. No key goes in metadata or LLM variables.

Browser API URLs are compiled into the frontend at image build time. Set NEXT_PUBLIC_API_BASE_URL as a Compose build argument before building; changing only a running container's environment does not update the bundle. NEXT_PUBLIC_API_URL remains accepted for existing local setups.

## Pre-release checks

1. Take and verify a PostgreSQL backup using the existing backup process. Test restoration in a separate database.
2. On a restored staging copy, inspect existing overlapping appointments, nonpositive time intervals, duplicate webhook IDs and duplicate clinic/call IDs. Migration intentionally fails rather than deleting or rewriting conflicting records.
3. Confirm old naive timestamps were stored as intended. Existing PostgreSQL timestamptz data is preserved; legacy SQLite timestamps cannot recover an unknown original timezone automatically.
4. Confirm PostgreSQL permits `CREATE EXTENSION btree_gist`. Have a database administrator enable it if the app role cannot. The overlap exclusion constraint requires this extension and obtains a table lock during installation; plan a maintenance window appropriate to table size.
5. Run the full backend suite against a disposable PostgreSQL test database, build both images, then perform the manual Retell acceptance guide with synthetic records.
6. Resolve current dependency advisories before release. Next.js 14 is preserved per scope; moving to a supported release requires an explicit follow-on stack upgrade. Do not run `npm audit fix --force` blindly.

Useful preflight queries on the staging copy:

```sql
SELECT a.id, b.id
FROM appointments a JOIN appointments b
  ON a.clinic_id=b.clinic_id AND a.provider_id=b.provider_id AND a.id<b.id
 AND a.start_time<b.end_time AND b.start_time<a.end_time
WHERE a.status<>'cancelled' AND b.status<>'cancelled';
SELECT id FROM appointments WHERE end_time<=start_time;
SELECT clinic_id, external_call_id, count(*) FROM call_logs
WHERE external_call_id IS NOT NULL GROUP BY 1,2 HAVING count(*)>1;
SELECT provider, external_event_id, count(*) FROM webhook_events
WHERE external_event_id IS NOT NULL GROUP BY 1,2 HAVING count(*)>1;
```

## Build and migrate

Use the existing Coolify Compose resource with `compose.prod.yaml`. The API startup runs `alembic upgrade head` before Gunicorn. For controlled releases, run migration once during the maintenance window before starting/restarting API replicas:

```sh
docker compose -f compose.prod.yaml build
docker compose -f compose.prod.yaml run --rm api alembic upgrade head
```

Do not issue production `up` or deploy until preflight and acceptance are approved. The provided commands build and migrate only when an authorized operator runs them. Never reset the database, remove persistent volumes, or seed demo data in production. Base.metadata.create_all is used only in isolated pytest setup; app startup performs no automatic schema creation.

The baseline migration now creates tables in dependency order. The additive Phase 1 revision adds provider working-hours/service mappings, optional call associations/lifecycle metadata, indexes, and PostgreSQL interval protection. Downgrades are deliberately disabled. Roll back app images only when schema-compatible; use a reviewed forward migration for schema changes. A database restore is an incident recovery action with potential data loss and must be separately authorized.

## Proxy, network and persistence

Keep Coolify HTTPS routes pointing to web port 3000 and API port 8000. Preserve the raw webhook body and X-Retell-Signature header through the proxy. Use standard certificate termination/renewal at Coolify. PostgreSQL and Redis have internal Docker networking and persistent named volumes; do not publish their ports to the internet. Redis AUTH/TLS, if used by the existing installation, must be represented in REDIS_URL and matched by the managed service configuration.

Keep rate/body-size protections at the proxy for unauthenticated requests and login traffic. Retell functions apply a Redis-backed per-call limit after authenticating signed clinic context; an unavailable limiter fails closed. Avoid proxy retries that mutate a write's key/arguments. Allow application validation and conflict responses through unchanged.

## Health, workers and logs

- `/api/v1/health/live` reports process liveness.
- `/api/v1/health/ready` checks PostgreSQL and Redis, returning 503 if unavailable.
- API starts only after healthy database/cache services; worker starts after API health.
- Web image runs a standalone Next.js production server as the node user.
- Worker stays alive and refreshes Redis heartbeat `dentalvoice:worker:heartbeat` with a 90-second expiry; failures retry with bounded connection timeouts. It is currently an idle maintenance worker; no booking is queued.
- Restart policy is unless-stopped. Docker health failures are observable but do not by themselves trigger Docker restart; configure Coolify monitoring/recovery accordingly.
- `docker compose -f compose.prod.yaml logs --tail=100 api worker web` exposes operational output. Retell function logging contains operation, generated correlation ID and status, not payload/phone/transcript. Restrict log access and retention.

After an authorized deployment, verify HTTPS live/ready URLs, JWT login with an actual clinic membership, clinic isolation, one test booking and conflict, staff reschedule/cancel, call event delivery and worker heartbeat. Record results. HTTPS, certificate routing, real account configuration and production backups were not validated in this local session.

## Localhost verification

```sh
cp .env.example .env
docker compose up --build
# In a second terminal, local demo only:
docker compose exec api python -m app.seed
```

Local startup requires Alembic migrations before API use. `make down` now preserves volumes. For default API tests, `cd apps/api` then `.venv/bin/python -m pytest -q` uses a temporary SQLite database; it never switches to application data. To assert concurrency, set TEST_POSTGRES_URL to a separate disposable test database with an empty public schema. The test runner creates/drops only random test schemas. See [testing](../testing/PHASE1_TESTING.md).

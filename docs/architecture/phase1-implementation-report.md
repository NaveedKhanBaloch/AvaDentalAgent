# Phase 1 implementation report

Date: 2026-10-23 (Asia/Karachi). **Local implementation verified; live Phase 1 acceptance is not complete. No production deployment or production data access occurred.**

## Architecture and audit

The existing Next.js/FastAPI/PostgreSQL/Redis/Retell monolith is retained. Repository inspection covered apps, docs, infrastructure, deployment/CI files and design-reference; empty scaffolding folders contain no alternative application implementations. The three requested architecture references and Phase 0 plan were reviewed. There is no separate completed Phase 0 report; existing security claims were verified against source rather than assumed. See [initial scheduling audit and plan](phase1-plan-and-audit.md).

The original 22 regressions passed, but the old session factory silently redirected database requests to a tracked local demo SQLite file after an invalid SQLAlchemy probe. That baseline touched local demo data; its tracked file was restored byte-for-byte from the clean starting Git revision. All subsequent tests use disposable databases. No production credentials were read or changed.

Both dashboard and allowed Retell booking writes call `services/scheduling.py`. It owns provider/service eligibility, clinic/provider windows, exceptions, duration, overlap and lifecycle. Routers own authentication, trusted clinic context and transaction completion. Audit records share the appointment transaction. Availability uses authoritative rows with per-provider prefetching rather than a database query per slot. Retell owns voice/conversation; no speech or LLM orchestration service was added.

## Scheduling and schema

ProviderWorkingHours and ProviderService are additive configuration tables. Empty schedule means inherit clinic hours, preserving existing behavior; an explicit schedule restricts available weekdays/windows. Empty service mapping preserves existing compatibility; otherwise listed clinic services are required. Catalog scheduling GET/PUT endpoints expose configuration under existing manage_schedule permission. Inactive/wrong-clinic/requested-missing provider or service fails without silent substitution. Omitted provider in availability returns eligible alternatives.

Clinic and provider windows intersect; clinic/provider exceptions block intervals. Minimum service duration is enforced; longer visits remain allowed. No new cancellation notice period, buffer, billing or clinical policy was invented. Overnight windows and cross-calendar visits work within configured windows. Timestamps are normalized to UTC for persistence and returned with offsets and clinic timezone. Ambiguous/nonexistent naive local timestamps fail closed; explicitly offset timestamps identify an instant. Ambiguous configured opening/closing boundaries fail closed. SQLite's timezone loss is handled only as a UTC test-adapter convention; unknown historical timestamp intent is not recoverable automatically.

Alembic revision `20261023_phase1` follows `20261023_phase0_baseline`. It adds scheduling tables, call associations/escalation/rank/processed time, provider-interval and event indexes, unique clinic/call identity and PostgreSQL interval constraints. Existing columns/tables are inspected so fresh baseline creation and existing schemas are both handled. The existing baseline's dependency order was corrected. No reset, destructive downgrade or production migration was run. Legacy duplicate/conflicting rows cause a safe failure for review; no automatic cleanup occurs. Fresh migration installation was tested on actual PostgreSQL; restored production-data migration rehearsals remain an operator requirement.

## Concurrency strategy

PostgreSQL btree_gist supports an exclusion constraint on `(clinic_id =, provider_id =, tstzrange(start_time,end_time,'[)') &&)` for noncancelled appointments. A positive interval check also applies. Adjoining appointments are permitted; overlapping intervals cannot both commit. Provider row locks serialize shared-service booking checks and configuration, while row locks serialize transitions of an existing appointment. The database constraint also rejects direct ORM inserts/updates that bypass the service. Cancelled appointments release the interval.

Retell idempotency takes a PostgreSQL transaction advisory lock scoped to clinic/call/operation/key. Request hash, authoritative response, patient intake, appointment, audit and call association commit in the same transaction. Repeating identical args returns the original committed appointment; changed args under the same key return conflict. A timeout produces no success assertion: retry the original action/key. SQLite tests do not claim this concurrency guarantee.

## Lifecycle specification

| State | Allowed next states |
|---|---|
| scheduled | confirmed, cancelled, no_show |
| confirmed | checked_in, completed, cancelled, no_show |
| checked_in | completed, cancelled |
| completed | none |
| cancelled | none |
| no_show | none |

Same-state updates are idempotent. New appointments must start scheduled/confirmed; unknown states are rejected. Completed/cancelled/no_show appointments cannot be rescheduled. DELETE remains a cancellation endpoint and now uses the same transition validation. Status-only cancellation still works after provider deactivation. Every shared-service mutation records before/after interval/provider/state, actor type/ID and timestamp in AuditLog atomically. History is available through a clinic-scoped API and dashboard. Existing create/update role permissions are retained; catalog mutations now enforce existing manage_schedule permission. These enforcement changes are intentional and documented.

## Retell functions and verification policy

[Retell contracts and dashboard guide](../api/RETELL_FUNCTIONS.md) documents every endpoint/alias, request/response, manual configuration, examples and troubleshooting. Official documentation was consulted for custom envelopes, raw-body signatures, event schemas and transfer behavior. Signed `call.agent_id` must match one enabled server-side integration; request/metadata patient/clinic identifiers are never credentials. Args-only payloads must be disabled. Signatures use the documented API-key + millisecond timestamp HMAC over raw bytes; the old sorted-JSON/separate-secret mechanism was replaced.

- General availability and approved clinic/catalog information are available to authenticated integration requests.
- New-intake booking collects minimum name/phone/catalog/slot details, requires strict boolean explicit confirmation and a stable key, and returns success only after commit.
- Existing-patient lookup, appointment retrieval, rescheduling, cancellation and legacy verify-patient return verification_required without patient enumeration. No approved OTP or authenticated-session-to-call bridge exists in this repository. These actions deliberately use human verification; staff can reschedule/cancel through the shared dashboard/API. No insecure demo verifier was invented.
- New intake does not silently merge a caller into an existing patient record by phone/name. Staff may need to reconcile duplicate intake records after verification.
- `request_human_assistance` (legacy create-followup endpoint retained) creates a real idempotent callback request in the existing queue, without associating an unverified patient or promising callback timing.

All original function paths remain. Intentional contract changes are signature authentication in every environment, trusted envelope context, explicit confirmation/idempotency for writes, no unverified patient disclosure and no webhook-created appointments. Domain failures are structured; auth/malformed-request errors preserve predictable HTTP detail responses. Redis per-call rate limiting is bounded and fails closed outside test mode. Operational logs use generated correlations and omit payloads/transcripts/phone numbers.

## Webhooks, call outcomes and handoff

See [call-processing specification](phase1-call-processing.md). Events are validated, clinic-scoped, transactionally serialized/deduplicated and monotonic: registered → ongoing → ended → analyzed. Missing timings can be filled by late events; stale lifecycle cannot overwrite newer state. No raw transcript/analysis is persisted and no patient is inferred from caller ID. Outcome booked comes from the booking transaction, not call analysis. Existing booked/missed/follow_up values remain; unresolved is explicit. Other reserved outcomes are not fabricated. Callback tools record escalation requested.

Retell's configured transfer tool/node remains the live transfer mechanism. No transfer destination or successful transfer was invented. Failed/unavailable transfers and verification failures use callback fallback. Clinic approval of emergency wording, routing and response commitments is still required; the code offers no diagnosis or patient-specific treatment instructions. The effective live agent type, version, phone destination, webhook level and event selection cannot be established from the demo agent ID in Git. No live Retell account was modified.

Webhook work is currently short transactional DB work dispatched outside the async event loop. No slow notifications or analysis jobs exist, so no unnecessary queue was introduced. The existing worker now remains alive, handles shutdown and records an observable Redis heartbeat; it is an idle maintenance worker, not a claimed full job processor. Booking transactions remain synchronous.

## Dashboard and deployment

The existing navigation/design remain. Initial data requests now carry the existing JWT. Appointment board shows provider, source, clinic-local time/timezone, validated status controls, rescheduling and history. Booking offers backend-calculated slot selection and clearly labels manual entry in the device timezone. Call view separates lifecycle/outcome and shows appointment/escalation details. AI booking, unresolved-call and reschedule metrics use actual stored records/audits. Empty/error states were added.

Production images build. The web image uses locked npm dependencies, standalone Next.js and a nonroot production server; Next.js was patched from 14.2.15 to 14.2.35, preserving Next.js 14/React 18. Backend packaging discovers all app subpackages and includes Gunicorn. Dockerignore excludes local databases, environments and dependencies. Compose preserves database/cache volumes, supplies missing JWT/Retell/CORS variables, builds the frontend URL correctly, adds dependency-aware readiness and worker health, and retains existing network/proxy ports. `make down` preserves volumes. Startup no longer calls create_all; Alembic owns schema. Demo seed CLI refuses production.

[Coolify instructions](../deployment/COOLIFY_HOSTINGER.md) cover backups/preflight, extension privileges, migration locking, secrets, HTTPS, persistence, health, logging and rollback. [Testing guide](../testing/PHASE1_TESTING.md) contains localhost commands and an isolated test Compose stack. No production deployment, certificate or external HTTPS route was tested.

## Executed verification

| Check | Observed result |
|---|---|
| Original baseline | 22 passed; local-demo fallback defect identified and repaired |
| Expanded backend suite with PostgreSQL enabled | 74 passed; includes 8 real PostgreSQL scenarios |
| PostgreSQL concurrency | Shared-service/direct writes: one winner for same provider, both winners for different providers; concurrent reschedules yield one winner; duplicate webhooks yield one event/call; simultaneous identical Retell retries return one committed appointment |
| Security/API regressions | Signature validity/expiry, clinic/role isolation, concurrent clinic requests, unverified data protection, confirmation, durable retries, conflict rollback and temporary-failure behavior passed |
| Headless Chrome against Docker stack | 2 passed: full login → availability → booking → history → reschedule → cancellation → calls, plus no-token redirect |
| Frontend production compilation | Next.js 14.2.35 build, TypeScript and lint passed inside Docker |
| Docker images | Backend and frontend built successfully |
| Runtime smoke | Gunicorn with two workers started; API readiness confirmed real PostgreSQL and Redis; worker heartbeat read back as alive |
| Compose | Test Compose configuration validated; production Compose configuration validated with example variables |
| Local availability timing | 30 authenticated localhost HTTP requests, p50 5.49 ms, p95 7.59 ms, max 7.67 ms on synthetic data |
| Dependency audit | 8 reported groups: 1 critical, 4 high, 3 moderate; major supported-framework remediation required |
| Live Retell calls/phone transfer | Not run; pending configured test agent and clinic-approved destination |

The latency sample is single-client local availability, not concurrent telephony load or production latency. Proposed staging budgets after this baseline: availability p95 <500 ms, synchronous write p95 <750 ms, with conflict/error ratios tracked under representative concurrency. These are targets, not achieved production claims. Python tests retain passlib crypt and Starlette test-client deprecation warnings. Browser visual QA inspected the appointment board screenshot; final controls retain the existing layout and disabled states.

## Acceptance and remaining work

Core scheduling, database overlap enforcement, lifecycle/history, authenticated new-intake AI booking, durable retries, private patient fallback, webhook verification/deduplication, real callbacks, dashboard flow, clinic isolation, migrations and local image/runtime checks are verified by the above tests.

**Release remains blocked** by current frontend dependency advisories under the mandated Next.js 14 stack, live Retell acceptance, clinic-approved verification/transfer/emergency configuration, and staging migration/security/performance rehearsal. The October 2026 upstream security update targets supported Next.js 15/16 releases; no unapproved major stack migration was made. A version patch does not make the current dependency audit clean. Some advisories are feature/platform dependent, but no blanket exemption is claimed.

Not every requested scenario is fully automated: real telephony disconnects/transfer failures, OTP/session verification, all mobile/assistive-device layouts, restored legacy-data migration, actual backend network timeout during commit and sustained multi-call load still need validation. Replaying the same analyzed event deliberately deduplicates it; corrected analysis revision handling is deferred. Legacy auth/change-password and other broader Phase 0 gaps are not declared complete. The callback queue provides safe fallback; automated existing-patient AI reschedule/cancel remains unavailable until approved verification exists.

No existing endpoints/navigation were removed. No billing, payroll, inventory, clinical module, separate voice engine or microservice was added. No production data/credentials or live agent were changed. Phase 2 was not started.

## Recommended follow-on work

Within Phase 1 release preparation: authorize a supported frontend framework upgrade, provision a test agent, approve caller verification and emergency/transfer policy, rehearse migrations on a backup, run live cross-channel calls and representative concurrency measurements. For Phase 2 consideration only: verified patient session bridge, retention controls, richer provider-calendar management, operational notifications with a durable outbox and approved delivery commitments. These recommendations are not implemented automatically.

## Files and checkpoint history

Checkpoint 1: `03c498e` shared scheduling, PostgreSQL migration/constraint, strict production context and isolated tests. Checkpoint 2: `b7b385a` secure Retell functions/idempotency/verification fallback and initial lifecycle handler. Checkpoint 3: `e1eafaa` call escalation visibility, worker lifecycle and processing specification. Checkpoint 4 includes dashboard, deployment, expanded end-to-end verification, security patch and documentation. Files are inventoried below.

- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `Makefile`
- `README.md`
- `apps/api/.dockerignore`
- `apps/api/Dockerfile`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/20261023_phase0_baseline.py`
- `apps/api/alembic/versions/20261023_phase1_scheduling.py`
- `apps/api/app/api/v1/routes/auth.py`
- `apps/api/app/api/v1/routes/catalog.py`
- `apps/api/app/api/v1/routes/dashboard.py`
- `apps/api/app/api/v1/routes/health.py`
- `apps/api/app/api/v1/routes/operations.py`
- `apps/api/app/api/v1/routes/patients.py`
- `apps/api/app/api/v1/routes/retell.py`
- `apps/api/app/api/v1/routes/scheduler.py`
- `apps/api/app/core/authorization.py`
- `apps/api/app/core/config.py`
- `apps/api/app/db/session.py`
- `apps/api/app/main.py`
- `apps/api/app/models/models.py`
- `apps/api/app/seed.py`
- `apps/api/app/services/retell.py`
- `apps/api/app/services/scheduling.py`
- `apps/api/app/workers/__main__.py`
- `apps/api/pyproject.toml`
- `apps/api/scripts/benchmark_phase1.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_authorization_phase1.py`
- `apps/api/tests/test_demo_flow.py`
- `apps/api/tests/test_postgres_concurrency.py`
- `apps/api/tests/test_retell_phase1.py`
- `apps/api/tests/test_scheduling_phase1.py`
- `apps/web/.dockerignore`
- `apps/web/Dockerfile`
- `apps/web/app/dashboard/page.tsx`
- `apps/web/app/login/page.tsx`
- `apps/web/next.config.mjs`
- `apps/web/package-lock.json`
- `apps/web/package.json`
- `apps/web/playwright.config.ts`
- `apps/web/tests/e2e/receptionist.spec.ts`
- `compose.prod.yaml`
- `compose.test.yaml`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/api/API_REFERENCE.md`
- `docs/api/RETELL_FUNCTIONS.md`
- `docs/architecture/current-app-audit.md`
- `docs/architecture/feature-gap-matrix.md`
- `docs/architecture/phase1-call-processing.md`
- `docs/architecture/phase1-implementation-report.md`
- `docs/architecture/phase1-plan-and-audit.md`
- `docs/deployment/COOLIFY_HOSTINGER.md`
- `docs/testing/PHASE1_TESTING.md`

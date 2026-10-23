# Phase 1 source audit and implementation plan

Inspected all top-level folders, backend routes/models/services/tests/migrations, frontend pages, infrastructure, Compose and documentation. Empty frontend modular folders are scaffolding; the dashboard is concentrated in app/dashboard/page.tsx. No AGENTS.md is present.

Phase 0 is partial: its plan exists but no separate completed implementation report exists. IMPLEMENTATION_STATUS.md is stale. Baseline: 22 existing tests pass. Important baseline defect: session initialization catches SQLAlchemy's invalid raw-string execution and silently falls back to dentalvoice_dev.db, even for an explicitly supplied test URL. The baseline therefore ran against local demo data; no production access occurred. Fix database selection before further tests and isolate every new run.

Existing states: scheduled, confirmed, checked_in, completed, cancelled, no_show. A transition map exists but DELETE and Retell bypass it. Only dashboard create/update take provider locks; Retell checks/inserts separately. Availability uses clinic hours and blocking exceptions, selects only the first provider, and has DST/SQLite timezone weaknesses. Writes ignore hours, duration and provider eligibility. No provider working-hours or service eligibility model exists. Webhooks incorrectly book appointments and synthesize patients. Caller name/phone lookup exposes patient data without verification. Follow-up endpoint returns a fabricated ID. Worker exits immediately. Authentication is optional and routes commonly select/create the demo clinic.

## Checkpoints

1. Shared availability/write validation, provider working hours and service compatibility, strict timezone handling, PostgreSQL exclusion constraint, transition validation and atomic audit. PostgreSQL tests use isolated schemas.
2. Authenticated integration binding, signed raw-body verification, official function envelope plus legacy args, durable idempotency and explicit confirmation. Sensitive patient operations use human verification fallback until an approved verification service exists.
3. Signature-verified call-event processing, atomic deduplication, monotonic lifecycle, real callback queue, transaction-derived outcomes. No webhook-created appointments.
4. Existing dashboard data additions, safe deployment configuration, migration/regression/build checks, integration guide and honest readiness report.

## Necessary contract/security changes

Production dashboard routes require JWT and active membership; existing roles remain. Cross-clinic records return 404. Booking enforces configured hours and minimum service duration. Naive ambiguous/nonexistent local timestamps are rejected. Retell requires authenticated integration context; caller identity is never established by phone/name or model arguments. Sensitive tools return verification_required with callback instructions. Booking requires confirmed=true and idempotency_key. Webhooks record call events only. Legacy endpoint paths remain.

## Schema changes

Add provider_working_hours/provider_services; optional call associations, escalation and lifecycle rank; unique clinic/call index; appointment positive-range check and PostgreSQL overlap exclusion. Existing duplicate/overlapping data causes migration failure for manual review, never deletion. Existing providers without explicit working hours inherit clinic hours; empty compatibility mapping means existing all-service behavior. No new cancellation notice period or buffer policy is invented.

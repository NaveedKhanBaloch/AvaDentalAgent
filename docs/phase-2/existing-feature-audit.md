# Phase 2 existing-feature audit

Status: pre-implementation review. Date: 2026-10-24, Asia/Karachi. No application code, migrations, permissions, production data or live Retell settings changed during this audit.

## Verified stack and earlier phases

Source confirms Next.js 14.2.35, React 18.2, TypeScript, Tailwind, Lucide; FastAPI, SQLAlchemy, Pydantic, PostgreSQL/psycopg, Alembic and Redis; Docker/Coolify configuration. Playwright is available for browser regressions. There is no existing PDF dependency. The worker only writes a Redis heartbeat; it is not a notification scheduler.

Phase 0 has a plan, not an independently completed acceptance report. Authentication, membership clinic context and permission helpers exist, but granular patient/operations permissions and credential-change functionality remain incomplete. Phase 1 added shared scheduling, PostgreSQL exclusion protection, lifecycle audit, confirmed/idempotent Retell booking, signed/deduplicated call events and callback fallback. Live Retell acceptance, approved caller verification and dependency-security remediation remain pending. Phase 2 must not label those earlier phases production-complete.

Baseline executed for this audit: `cd apps/api && .venv/bin/python -m pytest -q`: **66 passed, 8 skipped**, two deprecation warnings. PostgreSQL scenarios skipped because TEST_POSTGRES_URL was not provided; the historical Phase 1 report's 74-pass run is prior evidence, not a new result. Frontend build, browser regressions, Docker builds and migrations have not been rerun for this documentation-only checkpoint.

## Source feature matrix

| Area | Existing behavior | Gap / Phase 2 work | Main files |
|---|---|---|---|
| Patient list | Clinic-scoped text search across names/email/phone; returns all matches | Bounded server pagination, allowlisted sorting, status/date filters, appointment summaries | `apps/api/app/api/v1/routes/patients.py` |
| Patient identity | Canonical Patient with name, phone, email, contact preference, notes, created_at | Optional DOB, administrative status, opt-out flags, updated_at; no second patient identity | `apps/api/app/models/models.py`, `app/schemas/patient.py` |
| Patient UI | Create form, local search and directory with delete button | Profile/header/tabs, edit, status, related records, pagination and confirmation | `apps/web/app/dashboard/page.tsx` |
| Insurance | Clinic-checked patient insurance GET/POST | Current UI submits to patients[0]; require explicit selected patient and profile context | patient router and dashboard `handleInsuranceSubmit` |
| Audit | Shared helper adds/flushed AuditLog; scheduling commits it atomically | Patient create/update/delete call helper after commit, so audit may be rolled back on close; actor is system; no clinic_id on AuditLog | patient router, `app/core/audit.py` |
| Patient deletion | Actual db.delete/commit, despite audit metadata claiming soft_delete | Preserve/document DELETE contract; add reversible archive/restore separately, reviewed retention/deletion rules; protect related history | patient router |
| Timeline | Appointment-specific audit/history only | Patient-wide bounded timeline with stable timestamp/ID ordering, safe summaries, links and actor/source | scheduling service, AuditLog |
| Follow-ups | One existing FollowUp; clinic list capped at 10; create accepts patient or callback phone | Typed schemas, due date, type, links, creator/completion, revision, assignment validation; detail/update/status/filter UI | operations router, FollowUp |
| Retell callback | Idempotent real FollowUp creation inside signed function transaction | Extract/reuse shared follow-up creation service while preserving key scope and minimal unverified callback data | `app/api/v1/routes/retell.py`, `app/services/retell.py` |
| Recalls | No model, router, service or workspace | Distinct recall records/config, manual due dates, status/assignment, patient links and consent-aware sandbox preparation | new Phase 2 files |
| Communications | Scoped CallLog with optional verified patient/appointment associations | Profile shows only explicitly associated records; never correlate calls by phone/name | CallLog, operations router |
| Catalog money | DentalService.indicative_price is float | Add canonical Decimal/Numeric estimate pricing without breaking catalog responses or rewriting historical quotes | DentalService, catalog router |
| Estimates | No estimate entities, permissions, endpoints, versioning or PDFs | Complete independent module across database/service/API/UI, decimal totals, version-specific acknowledgement | new Phase 2 files |
| Dashboard | Existing scheduling/call metrics; FollowUp counts | Real Phase 2 metrics and role-aware rendering, no fabricated trends | dashboard router and page |
| Worker | Redis heartbeat with bounded retries | Optional deterministic database-backed reminder preparation; no real transport | `app/workers/__main__.py` |

## Relationships and security

Reuse Tenant → Clinic; Patient, Provider, DentalService, Appointment, InsuranceProfile, FollowUp and CallLog already carry clinic/tenant IDs. FollowUp has optional patient_id and assigned_user_id; it intentionally supports callbacks for unverified callers. Appointment references canonical patient/provider/service; CallLog has optional patient/appointment links. AuditLog has tenant_id and entity references but no direct clinic or patient reference. There are no ORM relationship loaders to reuse; SQLAlchemy queries are conventional.

Current roles are clinic_owner (including legacy “Clinic Owner”), receptionist, dentist, scheduler. Existing permissions include manage_staff, manage_schedule, view_financials, view_patients, create_appointments and update_appointments. Patient/operations routes receive authentication and clinic binding from main.py but do not consistently enforce dedicated read/write permissions. New granular permission grants require an explicit reviewed matrix, including enforcement on PDF/history/report endpoints. Frontend hiding is supplementary.

## Reuse boundaries and regressions to protect

Keep the dashboard shell/navigation/theme, existing patient and insurance routes, appointment service/lifecycle/history, Retell signatures/integration binding/idempotency, current FollowUp queue and worker/Redis infrastructure. Extract focused Phase 2 components instead of replacing the dashboard or adopting another component library.

Maintain `items` in list contracts while adding pagination metadata. Existing dashboard code currently assumes it fetched every patient: migrate both directory and booking patient selector together so pagination cannot silently hide selectable patients. Preserve no-patient callbacks. Do not show unverified call associations or financial values to unauthorized roles. Do not replace DELETE with archive silently. Archived status must never delete or cancel historical appointments/estimates.

Migration risks: the old baseline imports current model metadata, which makes fresh installs sensitive to future model additions; Phase 2 should use explicit new revisions and rehearse both a fresh install and an existing Phase 1 schema with synthetic representative data. Existing rows require safe active/default status, nullable due dates, and no retrospective invented consent. Catalog float conversion requires a documented decimal snapshot/backfill strategy. Financial updates need optimistic revision checks plus transactional locking. No migration may reset the database or remove existing columns.

## Required changes by checkpoint

A: patient/schema/router/service/audit improvements; bounded profile/timeline APIs; existing dashboard patient and insurance flows; additive migration and authorization/browser tests.

B: extend FollowUp, introduce separate Recall and clinic-approved policy/config; shared follow-up service including Retell adapter; complete workspaces and deterministic sandbox reminders with persistent deduplication.

C: Decimal catalog bridge, clinic estimate policy, estimate/items/immutable versions/history/acknowledgement; backend calculation and state services; protected PDFs; complete create/detail/revision/approval UI and real PostgreSQL concurrent-update tests.

D: permission-aware operational KPIs, cross-module profile links, full regressions/browser/mobile checks, Docker validation and final deliverables. Current deployment security blockers remain explicit until resolved under separate authorization.

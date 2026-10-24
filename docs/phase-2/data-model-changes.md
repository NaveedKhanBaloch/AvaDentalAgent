# Phase 2 data model changes

Date: 2026-10-24. Canonical entities remain in `apps/api/app/models/models.py`. No patient, clinic, staff, service or appointment subsystem was replaced.

| Entity | Changes and relationships |
|---|---|
| Patient | Optional DOB; active/archived status; contact opt-out and explicit email/SMS consent (false for existing records); archive actor/time; revision; updated_at. |
| AuditLog | Nullable clinic FK and patient attribution. Patient ID intentionally survives deletion as a historical identifier, without a patient FK. Legacy rows are retained with unknown context. |
| FollowUp | Existing table extended with due_at, extensible type, notes, appointment/call/estimate FKs, creator, completion actor/time, revision and updated_at. Patient remains optional for unverified callbacks. |
| Recall | Clinic/tenant/patient FKs, optional approved rule and completed-origin/current appointment FKs, manual/calculated due_date, contact preference, status, staff FK, last contact/completion attribution and revision. |
| RecallRule | Clinic FK, unique clinic/name, explicit interval_days and approving user/time. Rules are immutable configuration records; no default clinical interval. |
| ReminderPreparation | Clinic FK and logical source ID/type/revision/channel; unique tuple prevents duplicate preparation; prepared/suppressed state and safe reason. No transport or message content. |
| EstimatePolicy | Clinic PK/FK, currency, precision, approved tax labels/rates, discount ceiling, terms, optional validity, approving user/time and revision. |
| TreatmentEstimate | Clinic/tenant/patient FKs, unique clinic/number, lifecycle, current version, optimistic revision and creator/time. |
| EstimateVersion | Unique estimate/version; financial totals, clinic/patient/policy snapshots, dates, terms, reason, creator/time and version status. Issued financial content is immutable. |
| EstimateItem | Version/service FKs; treatment description snapshot; quantity Numeric(12,3), price/totals Numeric(18,4), discount/tax rates Numeric(7,4), stable position. |
| EstimateStatusHistory | Estimate/version FKs, previous/new status, actor, reason and timestamp; retained across revisions. |
| EstimateAcknowledgement | Unique version FK; administrative decision, person's name, method, recording actor/time. No legal-signature claim. |

Migrations follow `20261023_phase1`: `20261024_phase2a` (patients/audit/indexes), `phase2b` (follow-ups/recalls/rules/preparations), `phase2c` (estimates and follow-up estimate FK). Source files have explicit frozen declarations. The inherited Phase 0 baseline still imports current metadata; guards handle fresh installations, and a separate populated legacy-shaped migration test exercises actual column additions/table creation. Existing consent is never inferred. Patient updated_at is backfilled from registration; legacy follow-up updated_at receives migration time. No histories, DOB, clinical dates or audit actors are fabricated.

Indexes include clinic/status/registration, patient name, audit clinic/patient/time, operational clinic/due/patient and estimate clinic/patient/version relations. Searches use bounded ILIKE; there is no claim of optimized substring search at millions of records. Add measured trigram indexes in a later performance migration if needed.

Timestamps are timezone-aware except clinical calendar due/issue/expiry dates. IDs follow existing UUID-string conventions. All mutation plus audit writes share a transaction. No destructive downgrade: migration files deliberately require a reviewed forward migration to retain history. Use backups and a staging rehearsal before any future production migration.

Money calculation uses Decimal with configured 0–4 minor units and ROUND_HALF_UP. Per line: rounded quantity × price subtotal, rounded discount, rounded tax on discounted subtotal, then total; document totals sum those stored line values. Legacy catalog float prices are converted once using their decimal text into Numeric snapshots; no float arithmetic is used in estimate calculations. Catalog precision lost before Phase 2 cannot be recovered. Owner price overrides are validated and snapshotted.

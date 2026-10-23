> Historical baseline. For the source-verified Phase 1 findings, implementation and remaining release blockers, see [Phase 1 report](phase1-implementation-report.md) and [initial audit/plan](phase1-plan-and-audit.md). Earlier completeness claims below are not current acceptance evidence.

# Feature Gap Matrix

## Functional comparison table

| Functional area | Reference capability | Existing application capability | Status | Required changes | Backend dependencies | Frontend dependencies | Database impact | Complexity | Business value | Recommended priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Front-desk scheduling | Basic appointment booking and calendar flow | Appointment creation, status updates, availability checks, overlap validation | Already implemented | Keep and harden | `Appointment`, `Provider`, `ClinicBusinessHours` and route logic | Dashboard scheduling panel | Low | Medium | High | P0 |
| Patient master data | Patient intake, profile, lookup, insurance | Create, update, delete, search, insurance records | Already implemented | Harden validation and patient audit trail | `Patient`, `InsuranceProfile` | Patient management UI | Low | Medium | High | P0 |
| Clinic configuration | Multi-clinic settings, hours, service catalog | Tenant, clinic, provider, services, business hours | Already implemented | Add richer schedule rules and settings screens | `Clinic`, `Provider`, `DentalService`, `ClinicBusinessHours` | Admin settings pages | Low | Medium | High | P0 |
| Provider calendar controls | Calendar blocks and exceptions | Provider calendar block endpoints exist | Partially implemented | Add UI, recurring blocks, and stronger validation | `ScheduleException`, `Provider` | Provider calendar UI | Medium | Medium | High | P1 |
| Treatment catalog | Service menu and durations | Service catalog exists | Already implemented | Add treatment categories, pricing logic, attachments | `DentalService` | Services management UI | Low | Low | High | P0 |
| Billing and ledger | Financial tracking, receivables, payments | Not substantially implemented | Missing | Add invoice/payment modules | new models for invoices, ledger, payments | billing dashboard and forms | High | High | High | P2 |
| Clinical notes / dental charting | Clinical record and treatment tracking | Basic notes exist in patient data and appointment notes | Partially implemented | Add structured clinical notes, tooth/odontogram workflow | new clinical records tables | clinical notes tab | High | High | High | P2 |
| Treatment plan / treatment estimate | Quote and plan versioning | No structured treatment plan module | Missing | Introduce treatment plans and quote versions | new `treatment_plans`, `quote_versions`, `procedures` | treatment plan screens | High | High | High | P2 |
| Follow-up / recall workflows | Recall and follow-up queue | Call logs and follow-ups exist at a basic level | Partially implemented | Add recall rules, patient contact cadence, automation | `FollowUp` + recall tables | follow-up workspace | Medium | Medium | High | P1 |
| AI voice agent | Retell receptionist support | Integration routes and DB-backed booking exist | Partially implemented | Add auth, confirmation guardrails, event logging, human override | `RetellIntegration`, `CallLog`, `WebhookEvent`, appointment routes | AI status panel and call queue | Medium | Medium | High | P0 |
| Reporting and operations analytics | KPIs and reporting dashboards | Summary + analytics endpoints exist | Partially implemented | Add richer metrics, filters, exports | dashboard aggregates and reporting queries | executive dashboard screens | Medium | Medium | High | P1 |
| Staff permissions and RBAC | Role-based access and audit | Role dictionary exists; enforcement is partial | Partially implemented | Centralize permission service and apply to all sensitive routes | `Membership`, `User`, audit tables | role-based UI states | Medium | Medium | High | P0 |
| Audit and compliance tracking | Audit trail for sensitive actions | `AuditLog` model exists, but not fully wired | Partially implemented | Add action logging and retention policy | `AuditLog` and event model | admin logs screen | Medium | Medium | Medium | P1 |
| Insurance workflows | Insurance intake and profile management | Patient insurance records exist | Already implemented | Add claims, payer validation, eligibility checks | `InsuranceProfile` | insurance detail screens | Medium | Medium | High | P1 |
| Accounting export / compliance modules | Modules like accounting export, GST, country-specific compliance | Not present | Missing | Add module-specific domain models and exports | new external integration tables | compliance/admin screens | High | High | Medium | P3 |
| External integrations | Messaging, accounting, CRM, import modules | Basic calls and webhook events exist | Partially implemented | Add integration registry and secure credentials management | `WebhookEvent`, `RetellIntegration` plus service adapters | settings/integration screen | Medium | Medium | Medium | P2 |
| Consent and privacy | Patient consent and record access controls | Not yet explicit | Missing | Add consent records and access policy model | new `consents` and access controls | patient consent UI | High | Medium | High | P1 |
| Recall and no-show workflows | Automated reminders, no-shows, dedupe | Basic follow-up only | Missing | Add recall rules and outcome tracking | new no-show/recall models | operational queues | Medium | Medium | Medium | P1 |
| Multi-location expansion | Multi-clinic hierarchy and scheduling independence | Tenant/clinic model exists | Already implemented | Add clinic-level settings and staff assignment | `Clinic`, `Membership` | clinic switcher and settings | Medium | Medium | Medium | P1 |

---

## Summary of gap categories

### Already implemented

- patient management
- provider/service catalog
- basic scheduling and overlap prevention
- business hours and schedule exceptions
- insurance intake
- dashboard metrics
- basic AI-Retell integration scaffolding
- multi-tenant clinic foundations

### Partially implemented

- RBAC enforcement
- follow-up workflows
- AI call and webhook readiness
- calendar management UI
- analytics/reporting depth
- audit logging

### Missing

- billing and ledger workflow
- treatment plans and quote versions
- deeper clinical charting
- consent and privacy controls
- reporting exports and long-term KPI modeling
- compliance modules and external integrations

---

## Recommended strategy

Do not rebuild features that already work. Use the current foundation to extend in priority order:

1. tighten role permissions and auditability
2. strengthen AI and call-automation confirmation boundaries
3. expand treatment and follow-up flows
4. add billing and financial modules only after the practice core is stabilized
5. stage advanced clinical and compliance modules later

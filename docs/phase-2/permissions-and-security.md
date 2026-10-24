# Phase 2 permissions and security

Permissions extend the existing Phase 0 membership infrastructure, with no new role. Legacy `Clinic Owner` and canonical `clinic_owner` receive the same Phase 2 capabilities.

| Role | Patient | Follow-ups / recalls | Estimates | Operations report |
|---|---|---|---|---|
| Clinic owner | read/write/archive; delete only unreferenced | read/write | read/write/approve/admin | yes |
| Receptionist | read/write/archive | read/write | none | yes, without estimate counts |
| Scheduler | read | read/write | none | yes, without estimate counts |
| Dentist | read | read | none | no |

Existing scheduling permissions remain intact. Recall rule approval additionally requires existing manage_schedule. Policy creation requires an authenticated owner, even in demo mode. All new routers enforce server-side permissions; hiding buttons supplements these checks. PDF, history and related-record endpoints use the same clinic scoping as detail/list/mutations. Assignment requires active same-clinic membership; appointment/call/estimate links must match clinic and selected patient.

Strict auth or production requires bearer authentication and active clinic membership. The inherited explicitly non-strict local demo still permits unauthenticated demo access; do not use it for real patient data. Production compose retains STRICT_AUTH_MODE=true and DEMO_SEED_ENABLED=false.

Audit writes commit atomically with mutations and record current user/source plus changed field names, not copied patient notes or call transcripts. Timeline includes only safe summaries, verified call associations and financial events the role may read. Existing legacy audit context is not guessed. Hard-delete audit IDs remain without a patient FK; archived histories stay available under authorization.

Opt-out/archive block reminder preparation and recorded recall contact attempts. Email/SMS preparation also requires channel consent and a usable identifier. Consent defaults false for existing data. No real email/SMS/phone transport exists in this module; estimate delivery is an administrative record of delivery made elsewhere. Worker jobs use clinic transaction locks, stable batch scans, unique preparation keys and durable records; failures roll back and retry on the next cycle. Worker is disabled by default. Redis heartbeat and safe retry logs remain observable without patient content.

Estimate changes use row locks and revision checks; issued content and acknowledgements are version-specific. Financial fields use finite/bounded Decimal validation. PDFs escape user-entered text and have private no-store attachments. Administrative acknowledgements are not electronic signatures. No public share token, invoice/payment endpoint, voice financial disclosure, outbound campaign or external delivery service was added.

Inherited release blockers remain: Next.js 14 dependency advisories and Phase 1 live Retell/identity-bridge acceptance. This implementation does not remove those production release gates. No live credentials, production patient records or production services were used in verification.

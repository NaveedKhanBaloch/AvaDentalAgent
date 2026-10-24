# Phase 2 API contracts

Base: `/api/v1`. Bearer authentication and active membership select the clinic; clients cannot choose another clinic through request bodies. OpenAPI remains available at `/docs`. Validation errors are 422, missing/scoped-away records 404, insufficient permissions 403, missing strict-mode auth 401, stale revision/invalid transitions 409.

| Paths | Contract |
|---|---|
| `GET /patients` | Existing items retained; SQL pagination page/page_size (25/default, 100/max), total; search name/contact, status, registration dates, allowlisted sort/direction. Batched last completed and next active visit summaries. |
| `POST /patients`, `PATCH /patients/{id}` | Existing canonical intake/edit plus optional DOB, explicit consent/opt-out. PATCH permits clearing nullable values. expected_revision detects stale edits; optional only for legacy patient callers. |
| `GET /patients/{id}`, `/{id}/profile` | Scoped profile with open-follow-up count and last/next visit. |
| `POST /patients/{id}/archive`, `/restore` | Strict confirmed=true and expected_revision required. Does not cancel existing appointments. |
| `DELETE /patients/{id}` | Owner-only hard deletion retained for unreferenced records; 409 for referenced patients. Does not masquerade as archive. |
| `GET /patients/{id}/appointments`, `/communications`, `/follow-ups`, `/timeline` | Scoped, paginated related records. Communications require explicit patient association; no phone/name identity inference. Timeline contains safe event summaries, timestamp, actor/source and related ID. |
| `GET, POST /patients/{id}/insurance` | Existing policy intake on explicitly selected patient; mutations audited. |
| `GET /operations/capabilities` | Current permission list, clinic timezone and currency for UI visibility. |
| `GET, POST /operations/follow-ups`; `GET, PATCH /operations/follow-ups/{id}` | Extend existing queue. List search/status/priority/staff/patient/due-range/overdue and pagination. Fields: patient or callback phone, reason/type/priority/due_at with offset, assigned staff, appointment/call/estimate, notes. PATCH full typed form plus status and expected_revision. |
| `GET, POST /operations/recalls`; `GET, PATCH /operations/recalls/{id}` | Distinct future visits. Patient/type and approved due date or rule/completed origin required. Search/status/staff/patient/due-range/overdue/pagination. PATCH supports existing-contact attempt attribution, completion reason and expected_revision. |
| `GET, POST /operations/recall-rules` | Create immutable clinic-approved interval with authenticated approver; manage_schedule permission. |
| `POST /operations/reminders/prepare`, `GET /operations/reminders` | Sandbox preparation, unique source/revision/channel, paginated results API. Returns messages_sent=0 and transport=sandbox. No sending endpoint. |
| `GET /operations/metrics` | Real clinic-scoped patient/follow-up/recall counts; estimate status counts omitted without estimate_read. Includes timezone. |
| `GET, PUT /estimates/policy` | Owner policy configuration; authenticated explicit approval, matching clinic currency, finite approved rates, precision, discount cap and terms. expected_revision on update. |
| `POST /estimates/preview` | Backend totals for typed draft. Decimal strings returned; never calculate authoritative amounts in browser. |
| `GET, POST /estimates` | Search patient/number, patient/status/date filters, sort/direction, bounded page; create draft with patient_id, issue_date, optional valid_until and 1–100 catalog items. |
| `GET, PATCH /estimates/{id}` | Read version-specific document; PATCH current draft only with expected_revision. GET accepts version plus version_page/history_page, each bounded to 25 records, with totals. |
| `POST /estimates/{id}/revisions`, `/duplicate` | Authorized revision of issued document with required reason and revision; duplicate creates a new draft under current policy. Original snapshot/acknowledgement retained. |
| `POST /estimates/{id}/status` | expected_revision, version, strict confirmed and target status. Delivery method required for sent; acceptance/decline requires estimate_approve, name/method; expiry date verified in clinic timezone. |
| `GET /estimates/{id}/pdf?version=N` | Same clinic and estimate_read required; private binary attachment, no-store/nosniff. No public PDF URL. |

Follow-up lifecycle: pending → in_progress/completed/cancelled; in_progress → completed/cancelled. Recall lifecycle: due → contact_pending/contacted/scheduled/cancelled; contact_pending → contacted/scheduled/cancelled; contacted → contact_pending/scheduled/cancelled; scheduled → completed/contact_pending/cancelled. Completed/cancelled are terminal. Scheduled recalls require a same-patient active appointment; completion requires a completed visit or administrative reason. Approved interval = completed-origin local end date + configured days. No inferred clinical interval.

Estimate lifecycle: draft → sent/cancelled; sent → accepted/declined/expired/cancelled. Terminal documents may receive a new authorized revision, preserving old content and acknowledgements. Draft editing adds history but stays in the same version. All estimate update/status/revision requests use row locks and optimistic revision checks.

Retell's existing callback function uses the same follow-up domain service and retains its authenticated/idempotent contract. No new estimate disclosure or patient-status voice tool, dashboard configuration or live agent change is introduced. Future tools must use the existing verified-identity bridge, clinic binding, explicit confirmation and minimum necessary output.

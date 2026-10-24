# Phase 2 reference UI analysis

Date: 2026-10-24, Asia/Karachi. Status: reference research completed for implementation-plan review; this is not an implementation-completion report.

## Method, evidence and licensing

Used the supplied public-demo credentials only at [demo.dentalpin.com](https://demo.dentalpin.com). The first login attempt ran before hydration; a subsequent fully loaded login succeeded. Inspected authenticated navigation and existing records, opened unsaved patient/quote forms and a recall action menu. No records were created, changed, archived, approved or sent; no phone/email links were activated. Local browser-plugin execution was unavailable, so inspection used installed Playwright with headless Chrome. Screenshots are evaluation evidence only, not application assets. No repository source code, database implementation or proprietary assets were imported. The linked GitHub landing page could not be retrieved through the web tool; no clone was attempted.

Evidence labels:

- **Live**: visible in the authenticated demo during this audit; does not imply a mutation or delivery was tested.
- **Documentation**: a statement from an accessible published guide, not independently executed.
- **Proposed**: independently designed behavior for our application.
- **Unverified**: not accessible or not safely tested read-only.

The demo is shared and its sample values may change. Its monetary values, patient rows and clinical notes are not specifications or data to reproduce. Some supplied module directory URLs failed; the documentation portal exposed working screen-level URLs. Details below distinguish the current live interface from older documentation.

## Navigation and visual structure

**Live:** fixed left navigation, grouped clinical/financial/practice destinations, clinic header, public-demo banner, help, compact/theme controls and user/settings navigation. Patients and Recalls are under Clinical; Quotes under Financials; Reports under Practice. Home has appointment/recent-patient/recall panels and links into the relevant workspaces.

The inspected desktop screens use restrained borders, neutral backgrounds, compact typography, blue primary actions, a prominent page header and search/filter toolbar. Record identity/status sits left; dates/totals/actions sit right. Patient detail uses a persistent-looking identity header, tabs, a grid of summary cards and contextual links. Quote detail uses a main treatment column and totals/details sidebar. Screenshots were visually inspected for patient/detail and quote-list layout. These are general information-architecture observations; our rounded cards, Ava branding, theme and dashboard shell remain.

**Unverified:** mobile rendering and keyboard/screen-reader completeness in DentalPin, alternate-role visibility, tooltip contents, loading/error/empty states beyond the observed Activity loading state, mutation confirmations and server validation after saving. Documentation describes responsive behavior, but it is not live-tested evidence. Our implementation must independently test these states rather than copy assumptions.

## Screen inventory

### 1. Patients directory — Live

URL: https://demo.dentalpin.com/patients

Title Patients; New patient action; text search labeled Name or phone; status control; do-not-contact/debt toggles; last-visit sorting and direction. Entries show initials, patient identity, contact, status and sometimes a balance; linked rows open profiles. Pagination shows 20 of 29 records and page 1 of 2 with Previous/Next controls. Debt is reference-only and excluded from our nonfinancial roles and Phase 2 billing scope. The exact status-menu choices and filter persistence were not exercised.

Create opens an unsaved dialog with first/last name required, phone, email, ID document, birth date and notes; Cancel/Close and initially disabled Save are visible. No data was entered or saved. Duplicate detection and invalid-input responses remain unverified.

Screenshots: [directory](screenshots/reference-patients.png), [new-patient dialog](screenshots/reference-patient-create.png).

### 2. Patient profile and activity — Live + Documentation

Example inspected URL: https://demo.dentalpin.com/patients/d6eebc99-9c0b-4ef8-bb6d-6bb9bd380a46

Live header shows identity, age/contact, Edit and Actions. Tabs: Summary, Info, Clinical, Administration, Gallery, Activity. Summary has next/last visit and other module cards, quick actions, channel switches, attributed dated entries with context links and recall history. Clinical/ledger content is deliberately excluded from our Phase 2 scope. Current live terminology is Activity; the [patient detail guide](https://docs.dentalpin.com/user-manual/en/patients/screens/detail) describes History, demonstrating documentation drift.

The guide confirms an archive workflow and do-not-contact/channel restrictions; archive/restore and actual preference changes were not executed. Our archive design cannot simply copy the reference's deletion policy. Proposed administrative tabs and safe event summaries are in the implementation plan.

The Activity tab was opened: category filters were visible, followed by loading skeleton alerts. Loaded Activity results were not captured, so their final ordering/pagination remains unverified. Screenshots: [patient profile](screenshots/reference-patient-detail.png), [Activity loading state](screenshots/reference-patient-activity.png).

### 3. Recall workspace — Live + Documentation

URL: https://demo.dentalpin.com/recalls

Live title Call list; CSV action, month selector, reason/status/priority filters and overdue switch. Four counters summarize due-week, overdue, scheduled-month and conversion. Visible row: patient link, contact, priority, reason, state, due month and note; actions Call, No answer, Log attempt, Book appointment and Actions. Opening Actions revealed Snooze, Mark done and Cancel. No call/log/status/export action was executed.

The [screen guide](https://docs.dentalpin.com/user-manual/en/recalls/screens/recalls) describes contact outcomes, booking links, postponement and archived/opt-out exclusion. Reference state terminology includes pending and needs-review behavior; we will independently specify recall states rather than adopt that model. No distinct general callback-follow-up workspace was verified. Our FollowUp remains separate from future-visit Recall and appointment reminder.

Screenshots: [queue](screenshots/reference-recalls.png), [action menu](screenshots/reference-recall-actions.png).

### 4. Quote list — Live

URL: https://demo.dentalpin.com/budgets

Title Quotes; New quote; number/patient search, Filters, Created sort and descending control. Rows include quote number, version, patient, status, date, total/currency, payment-state badge and PDF icon; footer shows result count. Existing rows visibly include accepted, completed, rejected, sent and cancelled. They are observations, not our proposed transition map. Payment badges and invoice actions do not authorize a billing subsystem in our application.

The Filters menu, result sorting and downloads were not executed. This example had 13 records; quote pagination beyond that was not verified. Our lists will have explicit server pagination regardless.

Screenshot: [quote list](screenshots/reference-budgets.png).

### 5. New quote — Live

Opened via the visible New quote button. Required searchable patient selector and issue date; optional expiry date; separate patient-visible and internal note fields; Cancel and initially disabled Create and add treatments. This is a staged creation flow: the initial form does not show a complete treatment editor. No record was saved, so subsequent add/edit-item forms and their exact live validation are unverified.

Screenshot: [new quote form](screenshots/reference-quote-create.png).

### 6. Quote detail — Live + Documentation

Inspected an existing v2 accepted quote through a visible list link. Header includes number, version/status, linked patient, share/signature/invoice/more actions. Main column shows validity and treatment quantities/prices; sidebar has totals and creator/date metadata. A payments panel is present but is outside our scope. Buttons were observed, not executed.

The [detail guide](https://docs.dentalpin.com/user-manual/en/budget/screens/budgets_id) confirms draft item editing, version history, renegotiation, acceptance/rejection and PDF capabilities. The [module overview](https://docs.dentalpin.com/modules/) confirms versioned treatment quotes and PDFs; signatures are not a mandate to imitate legal signing. Our version-specific administrative acknowledgement will explicitly avoid that claim. Actual signature capture, PDF content, revision creation and message delivery remain unverified.

Screenshot: [quote detail](screenshots/reference-quote-detail.png).

### 7. Catalog and clinic configuration — Live + Documentation

Live Settings → Clinical links to Treatment Catalog and recall settings; clinic information is described as the data used in quotes/documents. The visible catalog link leads to https://demo.dentalpin.com/settings/catalog. The [catalog guide](https://docs.dentalpin.com/user-manual/en/catalog/screens/settings_catalog) confirms searchable/category-grouped treatments with configured prices, taxes and durations and role-restricted management. These are business capabilities, not a schema to copy. Our existing service catalog remains authoritative; new decimal price snapshots and owner-approved estimate policy are required.

Live catalog inspection additionally confirmed category expand/collapse controls, code/name search, category selection, New Treatment/Categories actions and grouped tables with code, name, price, tax type, duration and Edit controls. No catalog changes were attempted. Screenshots: [settings](screenshots/reference-settings.png), [clinical settings](screenshots/reference-clinical-settings.png), [catalog](screenshots/reference-catalog.png). We did not edit clinic tax settings or copy a universal recall interval.

### 8. Reports — Live

URL: https://demo.dentalpin.com/reports

Heading Dashboard with a period selector and Billing/Quotes/Schedule/Payments drill-down links. Cards, simple charts, date labels and numerical summaries are grouped by operational/financial topic. New-patient and scheduling indicators appear alongside financial reporting. Sample values are not reused; billing/payment reports remain excluded. Our Phase 2 dashboard will retain existing metrics and add only verified clinic-scoped patient/follow-up/recall/estimate aggregates, permission-filtered before serialization.

Screenshot: [reports](screenshots/reference-reports.png). Alternate date ranges, exports and drill-down behaviors were not executed.

### 9. Communications/contacts — Unverified

The supplied contacts directory and its screen guide did not load through the documentation tool; no standalone contacts navigation was exposed in the inspected demo. No claim is made about its fields, filters, messaging delivery or status workflow. Our Communications tab is independently scoped to permitted existing CallLog records and sandbox notification-preparation history. It will not assume caller identity from contact matching.

## Actions and workflow evidence boundary

Directly completed: public login; module navigation; open existing patient and quote; open unsaved patient/quote forms; open recall actions menu; inspect settings/catalog navigation. Not completed: save, edit, archive, send, approve/decline, call, contact logging, CSV export, PDF download, signature, reminder delivery or invoice creation. Therefore end-to-end mutation behavior is documentation-confirmed or unverified, never reported as live-tested.

No observed screen establishes our clinic's retention, tax, discount, consent or recall policy. These require independently reviewed configuration. The reference's partially different budget terminology (rejected versus our proposed declined, completed versus no treatment-execution state) will be documented explicitly rather than silently imported.

## Gaps and independently proposed components

| Reference functional pattern | Current gap | Original component proposal |
|---|---|---|
| Searchable, paginated patient directory | Unbounded API/local filter | PatientDirectory with server toolbar/pager and accessible row links |
| Patient identity and related-record workspace | No profile UI; insurance chooses first patient | PatientProfileHeader, scoped tabs, selected-patient insurance form |
| Attributed history/context links | No patient-wide timeline; patient audit transaction defect | PatientTimeline with SQL-backed cursor, safe event summary and context action |
| Workable recall queue | Only ten-record FollowUp list exists | Distinct FollowUpWorkspace and RecallWorkspace with shared visual table/form primitives |
| Consent-aware contact controls | Preference string only | Explicit opt-out/channel policy controls, sandbox preparation only |
| Quote list/form/detail | No estimates | EstimateList, ItemEditor, authoritative totals preview, VersionHistory, AcknowledgementDialog and protected PDF action |
| Period/metric drill-downs | Phase 1 metrics only | Operational KPI cards linking to scoped server filters; no unnecessary charts |

All proposed components include permission visibility, loading/empty/error states, validation, confirmations, pagination where appropriate and mobile/keyboard tests. No screenshot or DentalPin component is embedded into our application.

## Research limits and next step

The required reference analysis and existing gap analysis are prepared before implementation. Broader role/mobile/error/mutation exploration remains unverified and is not a blocker for independently designing the requested scope. Review [implementation-plan.md](implementation-plan.md), particularly Checkpoint A's permission/archive/delete compatibility decisions, before authorizing code changes.

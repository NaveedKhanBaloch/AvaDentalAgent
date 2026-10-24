# Phase 2 frontend components

The existing Next.js 14 / React 18 dashboard shell, branding, authentication, sidebar and Tailwind styles are retained. Components live in `apps/web/features/phase2/`; no additional UI framework or runtime dependency was introduced.

| Component | User workflow |
|---|---|
| Patients.tsx | Search/filter/sort/paginate directory; add/edit; archive/restore confirmation; URL-addressable patient profile; Overview, Appointments, Communications, Follow-ups, Insurance, Timeline and permission-gated Estimates tabs. Insurance binds the selected patient. Related data is loaded on tab selection, with paginated timeline/history. Estimate links open the selected document. |
| Tasks.tsx | Reused workspace for distinct follow-ups and recalls. Search/status/staff/date/priority/overdue filters, create/edit forms, patient lookup, appointment selection, verified call association, assigned staff, revision conflict reporting, explicit status confirmation and recorded contact attempt. Recall intervals require clinic approval and completed origin. Sandbox preparation clearly reports zero outbound messages. |
| Estimates.tsx | Search/status/date/sort/page; owner policy approval; patient/catalog item editor; decimal inputs and backend preview; edit draft, record delivery/acceptance/decline/expiry/cancellation, duplicate/revise, paginated version/status history, private PDF download. Policy missing disables creation and shows setup guidance. |
| Metrics.tsx | Adds real operations KPIs beside the original dashboard metrics. Estimate counts appear only for authorized roles; no invented chart series. |
| api.ts | Shared authenticated request/PDF helper and existing-theme form/panel styles; surfaces server validation/authorization/conflict errors. |

`app/dashboard/page.tsx` mounts modules using existing section routing and honors section/patient/estimate URLs. Booking's patient picker now supports server search with bounded results. The standalone insurance form also requires an explicit patient selection. Existing scheduling, providers, services, calls, staff and settings flows remain in their existing shell.

The existing shell now stacks the same navigation above the workspace below the medium breakpoint, preserving desktop sidebar behavior and allowing readable 390px content. Wide financial tables scroll inside the panel. Controls have labels, buttons and tab selection semantics; layouts wrap and tables scroll within panels. New modules include loading, empty and request-error states. Native confirmation/prompt dialogs provide explicit lifecycle confirmation. Financial totals are server-owned. Mobile screenshots and executed browser evidence are described in test-results.md; this is functional accessibility review, not a certified WCAG audit.

The React best-practices skill was applied: hooks stay unconditional, independent reads start independently, shared request logic is reused, related histories load only on demand, and large lists/history are paginated. Established React 18 APIs are retained. No network cache is shared between clinics.

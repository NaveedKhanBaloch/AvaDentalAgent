# Phase 2 test results

Verification date: 2026-10-24. Only synthetic records in disposable SQLite/PostgreSQL databases and the isolated `avadental-e2e` Docker project were used.

| Check | Executed result |
|---|---|
| Complete backend suite with TEST_POSTGRES_URL | **91 passed**, no skips, 2 dependency deprecation warnings; latest full run 9.76 seconds. |
| Final PostgreSQL migration/concurrency rerun | **11 passed**, including fresh migrations, populated legacy-shaped migration preservation, competing bookings/reschedules, duplicate Retell webhook/booking retries, simultaneous estimate edits and reminder deduplication. |
| Next.js production build | Passed locally and inside the Docker build, including TypeScript and framework lint checks. Final responsive-shell Docker build also passed. |
| Playwright combined suite | **5 passed in 7.5 seconds** on the final responsive-shell Docker stack; mobile panels also passed a usable-width assertion. |
| API/web Docker builds | Passed; isolated PostgreSQL, Redis, API, web and sandbox worker started successfully. Worker heartbeat healthy with sandbox preparation enabled. |
| PDF | Protected PDF bytes and extracted amounts/version/acknowledgement verified; 60 long descriptions retained across a 16-page PDF; text is escaped. Single-page and first/last long-page images rendered using PDFium and visually inspected. |
| Whitespace/source check | `git diff --check` passed. New Phase 2 Python routers/services/schemas passed Ruff with existing FastAPI Depends and timezone conventions (B008/UP017 excluded). |

Backend coverage includes patient registration/edit/nullable clearing, future DOB rejection, revision conflict, archive/restore, referenced delete refusal, audit transaction rollback, bounded timeline, follow-up lifecycle/assignment, optional unverified callback, recall approval-rule date calculation, illegal transitions, contact opt-out/consent revocation, role denials, cross-clinic related-record/PDF access, exact Decimal tax/discount totals, missing policy, NaN/discount bounds, immutable issued content, revision/acknowledgement retention, long PDF rendering and concurrency.

Browser scenarios exercise intake → patient profile → timeline/appointments; follow-up create/complete; recall creation and sandbox preparation; approved policy → catalog estimate → backend total preview → save → recorded delivery → acceptance → PDF download → revision → old-version acknowledgement. Existing appointment availability/booking/rescheduling/history/cancellation and token-free redirect remain covered. A separate UI capability-response test verifies hidden financial navigation/patient mutation and empty search results; it mocks capability visibility only. Actual role and cross-clinic enforcement are tested against FastAPI with distinct memberships.

Initial browser failures came from exact label selectors including select/textarea descendants and a mismatched policy button name; tests now use role/name selectors for those controls. PDF text extraction inserts layout whitespace/page footers, so the long-document assertion counts intact escaped tokens rather than assuming phrases remain adjacent across page breaks. The initial mobile overflow assertion alone missed clipping inside the existing shell: visual inspection found the fixed sidebar occupying most of a 390px screen. The shell now stacks navigation above content on small viewports, retains desktop layout and asserts usable main-panel width. Screenshots were recaptured after that correction.

Screenshots under `screenshots/implementation/` show original app UI using synthetic data. Reference-demo screenshots are separate and are not reused as product assets. Raw Playwright artifacts remain ignored under `apps/web/test-results/`.

Not claimed: live Retell phone acceptance, real outbound delivery, external signature legality, production database migration/rollout, full WCAG certification, CJK/complex-script PDF coverage, restore rehearsal using actual clinic data or production-scale performance/load tests. Existing Phase 1 release gates remain open.

Final visual review confirms full-width usable content at 390px after navigation stacks above the workspace; estimate tables scroll within their panels. Desktop screens retain the existing sidebar. [Mobile estimate](screenshots/implementation/estimate-mobile.png), [mobile recalls](screenshots/implementation/recalls-mobile.png), [desktop estimate](screenshots/implementation/estimate-desktop.png), [PDF](screenshots/implementation/estimate-pdf.png).

Localhost:3000 follow-up verification: all 5 browser tests passed in 7.2 seconds after exposing that port and allowing its API origin. Tested login, Phase 2 workflows and existing booking/rescheduling/cancellation using the actual local browser/API connection.

Native-development follow-up: the supplied traceback showed the host-run API resolving Docker-only `postgres`. Added dedicated persistent native dependencies on 55432/56379 and corrected native defaults; retained Docker URL overrides and removed conflicting test-app port 3000. Native API login returned HTTP 200 with Access-Control-Allow-Origin=http://localhost:3000. Both receptionist browser tests passed (5.7 seconds) against native Next.js:3000 / FastAPI:8000 with AdminPass123!, including authenticated booking/rescheduling/cancellation and unauthenticated redirect. Other project databases were not modified.

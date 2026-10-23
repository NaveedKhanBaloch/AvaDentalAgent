# Current Application Architecture Report

## Scope and method

This report is based on the repository itself as the source of truth, not on prior project notes or assumptions. It compares the existing codebase with the published DentalPin platform capabilities as a benchmark for feature planning and product gap analysis.

Important legal note: DentalPin is published under the Business Source License 1.1 and is not to be copied or reproduced in this project. The reference is used only for market benchmarking and high-level functional analysis.

---

## 1. Repository structure

Top-level structure:

- `apps/api` — FastAPI backend
- `apps/web` — Next.js dashboard frontend
- `infrastructure` — deployment helpers and Docker assets
- `docs` — project documentation and audit notes
- `design-reference` — UI reference assets
- `compose.yaml` / `compose.prod.yaml` — local and production Docker orchestration
- `.env.example` — environment configuration template

Backend structure:

- `apps/api/app/main.py` — FastAPI app bootstrap
- `apps/api/app/api/v1/routes/` — router modules for auth, patients, scheduling, staff, dashboard, operations, Retell, system, health
- `apps/api/app/models/models.py` — SQLAlchemy domain models
- `apps/api/app/core/` — configuration and security helpers
- `apps/api/app/db/` — database session and initialization
- `apps/api/app/services/` and `app/repositories/` — service/repository patterns
- `apps/api/app/seed.py` — demo seeding
- `apps/api/tests/` — pytest regression and smoke tests

Frontend structure:

- `apps/web/app/page.tsx` — landing page
- `apps/web/app/login/` — login experience
- `apps/web/app/dashboard/page.tsx` — primary clinic dashboard
- `apps/web/app/globals.css` — global styling and theme tokens
- `apps/web/components/`, `features/`, `hooks/`, `lib/` — modular frontend code

---

## 2. Frontend framework

The frontend is a Next.js 14 application using:

- Next.js 14.2.15
- React 18
- TypeScript
- Tailwind CSS
- Lucide React icons
- Fetch-based API integration against the FastAPI backend

The dashboard is implemented as a single functional admin shell with sections for:

- dashboard summary
- patients
- appointments
- providers
- services
- insurance
- calls
- staff
- settings

The theme toggle is implemented client-side using localStorage and a light/dark class toggle on the document root.

---

## 3. Backend architecture

The backend is a modular FastAPI monolith built around:

- API routers under `app/api/v1/routes/`
- SQLAlchemy models under `app/models/models.py`
- Pydantic schemas under `app/schemas/`
- security config under `app/core/security.py` and `app/core/config.py`
- DB session and init under `app/db/`
- seed data under `app/seed.py`

Primary app bootstrap:

- `apps/api/app/main.py` creates the FastAPI app
- startup event runs `Base.metadata.create_all()` and `seed_demo_data()`
- routers are included under `/api/v1`

This is a monolith-first architecture with tenant-aware data access patterns, but not yet a full service-layer extraction for every domain.

---

## 4. Database models

The repository contains a rich domain model centered on dental operations.

Core entities:

- `Tenant` — multi-tenant boundary
- `Clinic` — clinic profile and settings
- `User` — user identity
- `Membership` — user-to-tenant/clinic role assignment
- `Provider` — clinician or provider profile
- `DentalService` — treatment/service catalog
- `Patient` — patient record
- `Appointment` — appointment lifecycle
- `InsuranceProfile` — patient insurance intake
- `ClinicBusinessHours` — operating hours
- `ScheduleException` — provider time blocks / closures
- `RetellIntegration` — AI call configuration metadata
- `CallLog` — inbound/outbound call history
- `FollowUp` — patient follow-up tracking
- `AuditLog` — action audit trail
- `WebhookEvent` — external event traceability
- `IdempotencyRecord` — request deduplication support

This domain is already aligned to a dental practice management core and includes AI/voice integration hooks.

---

## 5. Existing API endpoints

The current backend has these main route groups:

### Health and system

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/system/info`

### Authentication

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/change-password`

### Patient workflows

- `GET /api/v1/patients`
- `POST /api/v1/patients`
- `GET /api/v1/patients/{patient_id}`
- `PATCH /api/v1/patients/{patient_id}`
- `DELETE /api/v1/patients/{patient_id}`
- `GET /api/v1/patients/{patient_id}/insurance`
- `POST /api/v1/patients/{patient_id}/insurance`

### Appointment workflows

- `POST /api/v1/appointments/availability`
- `GET /api/v1/appointments`
- `GET /api/v1/appointments/{appointment_id}`
- `PATCH /api/v1/appointments/{appointment_id}`
- `PATCH /api/v1/appointments/{appointment_id}/status`
- `DELETE /api/v1/appointments/{appointment_id}`
- `POST /api/v1/appointments`

### Catalog and schedule management

- `GET /api/v1/providers`
- `POST /api/v1/providers`
- `PATCH /api/v1/providers/{provider_id}`
- `DELETE /api/v1/providers/{provider_id}`
- `GET /api/v1/services`
- `POST /api/v1/services`
- `PATCH /api/v1/services/{service_id}`
- `DELETE /api/v1/services/{service_id}`
- `GET /api/v1/business-hours`
- `POST /api/v1/providers/{provider_id}/calendar/blocks`
- `GET /api/v1/providers/{provider_id}/calendar`

### Dashboard and operations

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/analytics`
- `GET /api/v1/operations/calls`
- `POST /api/v1/operations/calls`
- `GET /api/v1/operations/follow-ups`
- `POST /api/v1/operations/follow-ups`

### Retell integration

- `POST /api/v1/integrations/retell/functions/check_availability`
- `POST /api/v1/integrations/retell/functions/book_appointment`
- `POST /api/v1/integrations/retell/functions/lookup_patient`
- `POST /api/v1/integrations/retell/functions/get_appointment`
- `POST /api/v1/integrations/retell/functions/reschedule_appointment`
- `POST /api/v1/integrations/retell/functions/cancel_appointment`
- `POST /api/v1/integrations/retell/functions/get_treatment_information`
- `POST /api/v1/integrations/retell/functions/get_clinic_information`
- `POST /api/v1/integrations/retell/webhooks`

---

## 6. Authentication

Authentication is implemented with JWT and OAuth2 password flow.

Implementation elements:

- `OAuth2PasswordBearer` in `apps/api/app/api/v1/routes/auth.py`
- token generation through `create_access_token`
- password hashing via `passlib`
- `get_current_user` validates bearer tokens and resolves user identity
- demo admin login is seeded using configured credentials from environment settings

This provides a working app-level auth shell, but not yet a production-grade tenant-aware RBAC enforcement in every route.

---

## 7. Authorization and roles

The repository includes role definitions and permission hooks:

- `Membership.role`
- `PERMISSIONS_BY_ROLE` in `apps/api/app/api/v1/routes/staff.py`
- `require_permission()` helper used for schedule-related access checks

Roles present include:

- `clinic_owner`
- `receptionist`
- `dentist`
- `scheduler`

Permission model exists, but the project does not yet appear to enforce consistent role checks across all patient, appointment, and admin actions.

---

## 8. Appointment workflows

The current app already supports:

- availability checks by date and time window
- provider-based schedule checks
- appointment creation with overlap prevention
- appointment status updates
- cancellation
- dashboard list generation

Business logic currently includes:

- patient lookup by ID
- default provider/service assignment when not specified
- overlap detection for same-provider conflicts
- appointment status normalization

This is a solid front-desk scheduling foundation, but it is not yet equivalent to a full practice scheduler with advanced rules, EMR attachment, recall, recurring schedules, or clinician-specific calendars.

---

## 9. Patient workflows

Patient handling includes:

- create patient
- list/search patients
- get patient
- update patient
- delete patient
- insurance intake
- preferred contact method
- notes

The data model supports a proper patient record and insurance profile pattern. Search is implemented by name, email, and phone.

---

## 10. Clinic configuration

Clinic support is already present with:

- tenant and clinic identity
- clinic phone/email/address
- timezone and currency
- clinic business hours
- schedule exceptions
- specialty/provider definitions

This supports a likely multi-tenant dental clinic configuration model.

---

## 11. Available UI pages

The frontend currently includes:

- landing page
- login page
- dashboard shell

The dashboard contains operational panels for:

- appointments
- patients
- providers
- services
- insurance
- calls
- staff
- settings

The current UI is a strong operations dashboard, but not yet a complete clinical or financial workspace.

---

## 12. Dashboard metrics

Current summary metrics include:

- appointments_today
- upcoming
- pending_confirmations
- cancelled
- new_patients
- calls_handled
- missed_calls
- follow_up_requests

Analytics include:

- appointment trends over the last seven days
- call outcome counts: booked, missed, follow_up

This is appropriate for front-desk operations and AI call tracking.

---

## 13. Retell integration readiness

The repository includes a dedicated Retell integration module with:

- route definitions for function-call endpoints
- webhook handling
- data-backed appointment creation and patient lookup logic
- clinic and treatment information access
- call log and follow-up patterns

The backend currently has the right architectural shape for a voice-agent receptionist, with DB-backed scheduling operations and patient retrieval. This is a solid base for further authorization and validation hardening.

Current readiness status: partially implemented and functionally close to working, but not yet production-hardened against all voice-agent edge cases.

---

## 14. Docker / Coolify configuration

The local Docker stack includes:

- PostgreSQL
- Redis
- API service
- worker service
- web frontend service

The project includes local Compose config and likely a production deployment pattern for VPS/Coolify. The repo also contains infrastructure doc files under `docs/deployment/` and `infrastructure/` for deployment planning.

The app is set up to be Docker-friendly, which aligns with a VPS + Coolify deployment model.

---

## 15. Automated tests

The repository includes backend tests under `apps/api/tests/`.

Current test coverage focuses on:

- health checks
- demo flow validation
- appointment scheduling behavior
- Retell function alias validation

The project already has a meaningful regression suite for critical scheduling and Retell flows.

---

## 16. Existing custom features

Notable custom features already in the repo:

- multi-tenant clinic foundation
- AI/Retell receptionist flow hooks
- provider and service catalog management
- manual fallback dashboard for admin operations
- patient insurance intake
- follow-up tracking
- call logging and operational dashboard
- dark/light theme toggle
- strong dashboard visual identity and SaaS-style UX

This is not a blank repository; it is a working dental front-desk management MVP with AI assistant hooks.

---

## 17. High-level assessment

This project is already meaningfully advanced beyond a generic starter app. It contains:

- a real domain model for dental operations
- booking and scheduling logic
- patient and insurance data
- AI call integration hooks
- clinic operations and staff concepts
- a usable dashboard
- Docker deployment structure

The main gap versus a full dental practice management platform is the expansion of deeper clinical, billing, consent, financial, and operational features rather than basic infrastructure work.


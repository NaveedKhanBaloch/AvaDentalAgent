# API Reference

## Base URL

- Local: http://localhost:8000
- API prefix: /api/v1

## Health

- GET /api/v1/health/live
- GET /api/v1/health/ready

## System

- GET /api/v1/system/info

## Authentication

- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
- POST /api/v1/auth/change-password

## Appointments

- POST /api/v1/appointments/availability
- GET /api/v1/appointments
- GET /api/v1/appointments/{appointment_id}
- POST /api/v1/appointments

## Dashboard

- GET /api/v1/dashboard/summary
- GET /api/v1/dashboard/analytics

## Retell integration

- POST /api/v1/integrations/retell/functions/check-availability
- POST /api/v1/integrations/retell/functions/create-appointment
- POST /api/v1/integrations/retell/functions/verify-patient
- POST /api/v1/integrations/retell/functions/get-appointment
- POST /api/v1/integrations/retell/functions/reschedule-appointment
- POST /api/v1/integrations/retell/functions/cancel-appointment
- POST /api/v1/integrations/retell/functions/create-followup
- POST /api/v1/integrations/retell/webhooks

## Phase 1 contract changes

Production dashboard routes require JWT + active clinic membership. Existing create/update appointment permissions remain, and catalog/schedule mutations enforce existing manage_schedule permission. Unauthenticated demo access is limited to nonproduction configurations with strict auth disabled. Sensitive object reads/writes are clinic-scoped.

Additional scheduling endpoints:

- PATCH /api/v1/appointments/{appointment_id}
- PATCH /api/v1/appointments/{appointment_id}/status
- DELETE /api/v1/appointments/{appointment_id} (validated cancellation, no hard deletion)
- GET /api/v1/appointments/{appointment_id}/history
- GET /api/v1/providers/{provider_id}/scheduling
- PUT /api/v1/providers/{provider_id}/scheduling

Provider scheduling configuration is `{working_hours:[{weekday:0,opening_time:"08:00",closing_time:"17:00"}],service_ids:["SERVICE_ID"]}` in clinic local time. Empty working_hours means inherit clinic hours; otherwise an unlisted weekday is unavailable. Empty service_ids preserves all-service compatibility; otherwise only listed active clinic services are eligible. Overnight windows have closing_time earlier than opening_time. Clinic windows still bound provider windows. Clinic/provider exceptions block overlapping intervals.

Appointments must be at least the configured service duration; longer intervals are accepted within working hours. New appointments start scheduled/confirmed; completed/cancelled/no_show cannot be rescheduled. Unknown states are rejected rather than silently normalized. Returned scheduling timestamps include offsets and a timezone name; naive ambiguous/nonexistent DST inputs are rejected. Existing date fields and all existing routes remain.

The availability response retains success/status/message/slots and adds timezone plus provider IDs. Appointment listings add end_time, patient/provider/service IDs, source and timezone. Call listings add appointment association, escalation and processing time. Summary adds ai_bookings, rescheduled and unresolved_calls. No metric implies a confirmed transfer or verified patient unless that state actually exists.

Retell auth, explicit confirmation, new-intake-only booking, privacy fallback and webhook behavior have intentional security changes; use the complete [Retell contract guide](RETELL_FUNCTIONS.md). Webhooks never create bookings. The old change-password route remains a stub; do not use it as an actual password-change implementation.

## Phase 2 patient operations and estimates

See [Phase 2 API contracts](../phase-2/api-contracts.md) for patient profiles/timelines, follow-ups, recalls, operations metrics, estimate policy/lifecycle/versioning and protected PDF endpoints. Existing paths remain; patient lists are now paginated (items wrapper retained).

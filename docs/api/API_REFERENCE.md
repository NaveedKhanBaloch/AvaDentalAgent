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

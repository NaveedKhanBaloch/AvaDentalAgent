# Phase 0 hardening plan

## Objective

Stabilize the existing dental clinic management platform before additional feature work. This is a security, reliability, and operational readiness pass only.

## Scope

- confirm actual stack and repository state
- verify database init behavior and migration strategy
- centralize permissions and clinic-scoped authorization
- reduce tenant isolation risks
- add consistent audit logging for sensitive actions
- harden validation and Retell integration security
- expand regression coverage without altering user workflows
- review deployment and health checks

## Non-goals

- no new business module creation
- no UI redesign or brand change
- no endpoint removal or contract-breaking changes
- no production deployment during Phase 0
- no destructive DB resets or production data changes

## Work sequence

1. Audit and confirm repository architecture, models, and startup behavior.
2. Add safe migration support and production guardrails around demo seeding.
3. Centralize authorization helpers and enforce clinic-scoped access checks.
4. Add audit logging for sensitive actions and improve validation.
5. Harden Retell auth and webhook validation without altering supported function names.
6. Add focused regression tests for auth, clinic isolation, and concurrency.
7. Validate Docker startup and backend test suite.

## Constraints

- preserve the current FastAPI + Next.js + SQLAlchemy stack
- preserve current API routes and Retell aliases
- keep demo data available in development only
- do not run destructive migration commands against populated production data

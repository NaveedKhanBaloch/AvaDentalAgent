# DentalVoice AI

DentalVoice AI is a multi-tenant dental clinic SaaS MVP for local deployment. It includes a FastAPI backend, a Next.js dashboard, PostgreSQL persistence, Redis-backed jobs, and Docker Compose setup for local development.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui-inspired components
- Backend: FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PostgreSQL
- Jobs: Redis + background worker
- Local orchestration: Docker Compose

## Local development

1. Copy `.env.example` to `.env` and adjust values.
2. Start containers:
   - `docker compose up --build`
3. Frontend: http://localhost:3000
4. API: http://localhost:8000
5. Swagger: http://localhost:8000/docs

## Demo admin login

- Email: `admin@harbordentaldemo.local`
- Password: `AdminPass123!`

## Project structure

- `apps/api`: FastAPI monolith backend
- `apps/web`: Next.js dashboard frontend
- `infrastructure`: deployment helpers and Docker assets
- `docs`: architecture, API docs, deployment notes, testing instructions

## Scripts

- `make up` to start local services
- `make down` to stop and remove volumes
- `make api-test`
- `make web-test`
- `make lint`

## Status

This repository contains the foundation for a working MVP, including project structure, Docker setup, backend APIs, and frontend shell. It is intended for iterative implementation and local development.


Phase 1: see [implementation report](docs/architecture/phase1-implementation-report.md), [Retell configuration](docs/api/RETELL_FUNCTIONS.md), [test commands](docs/testing/PHASE1_TESTING.md), and [Coolify preparation](docs/deployment/COOLIFY_HOSTINGER.md). Run Alembic migrations before starting the API; it no longer creates schema on startup or silently switches databases. For an isolated synthetic stack use `docker compose -f compose.test.yaml up --build -d --wait`. Do not use the test Compose file in production.

## Native development database hostname

For Next.js on localhost:3000 and uvicorn on localhost:8000, start dedicated dependencies with `docker compose -f compose.local.yaml up -d --wait`. Native API defaults use PostgreSQL at 127.0.0.1:55432 and Redis at 127.0.0.1:56379; Docker service hostnames `postgres` and `redis` only resolve inside their Docker network. See [native login/setup instructions](docs/phase-2/deployment-notes.md#native-development-login-port-3000). The native demo password is `AdminPass123!`; the isolated test app on port 33001 uses a separate database and password.

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

# Coolify + Hostinger deployment guide

## Prerequisites

- Hostinger VPS with Docker support
- Coolify installed and configured
- A Git repository with the monorepo
- Domain names for frontend and API

## Steps

1. Connect the repository to Coolify.
2. Set environment variables from `.env.example`.
3. Configure a Compose-based deployment.
4. Add Postgres and Redis persistence volumes.
5. Route API and web domains through the reverse proxy.
6. Run database migrations via the API container or a migration command.
7. Seed demo data in the development environment only.

## Suggested variables

- DATABASE_URL
- REDIS_URL
- SECRET_KEY
- JWT_SECRET_KEY
- RETELL_API_KEY
- RETELL_WEBHOOK_SECRET

## Health checks

- API: http://localhost:8000/api/v1/health/live
- Web: http://localhost:3000

## Rollback

- Keep previous image tags
- Revert Compose config and redeploy from last known-good commit
- Restore Postgres volume from backup

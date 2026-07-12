# TG Scheduler

Telegram Mini App for scheduling announcements in channels

## Stack

- **Backend:** FastAPI, uv
- **Frontend:** React 19, Vite, Tailwind
- **Infra:** Docker Compose, Traefik, PostgreSQL, Valkey

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

- API health: http://localhost:8000/health
- Frontend: http://localhost:3000

## Local dev

```bash
# Backend
cd backend && uv sync && uv run python -m app.main_api

# Frontend
cd frontend && npm install && npm run dev
```

## Structure

```
backend/     FastAPI (health endpoint)
frontend/    React SPA stub
traefik/     Reverse proxy
```

> This is **scaffold**


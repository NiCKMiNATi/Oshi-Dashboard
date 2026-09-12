# Oshi Dashboard v0.1 scope

Source: `OSHI_SYNC_V1`, `TYPE:TASK`, `DIR:C2X`, project `Oshi Dashboard`, version `0.1`.

Goal: initialize a local development project and backend foundation for a private personal oshi-information dashboard.

## Stack and structure

- Frontend: Next.js, TypeScript, App Router; scaffold only.
- Backend: FastAPI, Python, SQLAlchemy, SQLite.
- Mode: dark-only, desktop-first, local-only, no authentication.
- Required directories: `frontend/`, `backend/`, `scripts/`, `data/`, `docs/`.
- Required root documentation: `AGENTS.md`, `README.md`.

## Models

```text
Oshi(id, name, type, priority, active, created_at)
Keyword(id, oshi_id, value, weight)
Update(id, title, summary, category, source, source_url, published_at,
       start_date, end_date, deadline, location, relevance_score, status, created_at)
UpdateOshi(update_id, oshi_id)
```

Oshi types: `ANIME`, `CHARACTER`, `GAME`, `IDOL`, `SEIYUU`, `ARTIST`, `MANGA`, `OTHER`.

Update categories: `NEWS`, `EVENT`, `MERCH`, `COLLAB`, `MOVIE`, `RELEASE`, `OTHER`.

Update statuses: `NEW`, `SAVED`, `INTERESTED`, `GOING`, `BOUGHT`, `IGNORED`.

## Required API

```text
GET    /api/oshi
POST   /api/oshi
PATCH  /api/oshi/{id}
DELETE /api/oshi/{id}
GET    /api/updates
GET    /api/updates/{id}
POST   /api/updates
PATCH  /api/updates/{id}
PATCH  /api/updates/{id}/status
GET    /api/stats
```

Update filters: `oshi`, `category`, `status`, `min_score`.

Scoring: followed oshi +40; priority keyword +25; Japan event +20; action deadline +20; merchandise +10; irrelevant editorial −30; clamp 0–100.

## Deliverables and exclusions

Initialize the repository, document conventions, implement the backend/database/models/schemas/routes, seed samples for 進撃の巨人, 原神, and Ryujin, add backend unit/API tests, and report changes, verification, decisions, and blockers.

Do not implement MSN ingestion, authentication, deployment, PostgreSQL, or frontend features beyond initial scaffolding. Avoid elaborate abstractions.

Reserved for later: `oshi kaishi`, `oshi shuuryou`, `oshi saikidou`, `oshi status`, `oshi hiraku`, `oshi test`.

Design reference for a later milestone: [Figma](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk).

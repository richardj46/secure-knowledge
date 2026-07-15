# SecureKnowledge

Production-grade permission-aware knowledge assistant monorepo.

## Applications

- `apps/api` — FastAPI backend
- `apps/worker` — asynchronous ingestion and processing worker
- `apps/web` — React + TypeScript frontend

## Shared package

- `packages/secure_knowledge` — reusable Python modules shared by the API and worker

## Local startup

```bash
cp .env.example .env
docker compose up --build
```

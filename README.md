# START AI

START AI is a foundation scaffold for an MVP that analyzes sprint start videos and evaluates running mechanics.

This repository intentionally focuses on architecture, structure, and placeholder flows rather than full pose detection or biomechanical scoring.

## Stack

- Frontend: Next.js App Router + Tailwind CSS
- Backend: FastAPI
- Database: PostgreSQL
- Storage: S3-compatible interface with local mock storage
- Auth: email/password with JWT

## Folder Structure

```text
start-ai/
  frontend/
    src/
      app/
      components/
      lib/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      workers/
  docker-compose.yml
```

## Local Run

### 1. Start PostgreSQL

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai
docker compose up -d db
```

### 2. Run the backend

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### 3. Run the frontend

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## Production Deployment

The current app is ready to be deployed as two services:

- `frontend/`: Next.js web app
- `backend/`: FastAPI API

Recommended production shape:

1. Deploy PostgreSQL as a managed database
2. Deploy `backend/` as a web service with these env vars:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `MOCK_STORAGE_DIR=/app/uploads`
3. Deploy `frontend/` as a web service with:
   - `INTERNAL_API_BASE_URL=https://<your-backend-domain>/api/v1`

Both `frontend/` and `backend/` include Dockerfiles for deployment.

### Notes

- `DATABASE_URL` may be provided as `postgres://...` or `postgresql://...`; the backend normalizes it for `asyncpg`.
- Uploaded videos are currently stored on the service filesystem via `MOCK_STORAGE_DIR`, so persistent object storage should be added before a full production launch.
- For public deployment, the frontend should call the backend through `INTERNAL_API_BASE_URL`.

## MVP Foundation Included

- Email/password auth UI and API skeleton
- Dashboard page with mock analysis summary
- Video upload page with single main CTA
- FastAPI upload endpoint with metadata persistence
- Placeholder async-ready analysis dispatch
- Result page with dummy mechanics data

## Not Implemented Yet

- Real pose detection
- Real scoring engine
- Production S3 integration
- Background worker queue such as Celery or Dramatiq
- Email verification and password reset

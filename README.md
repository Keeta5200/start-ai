# START AI

START AI is a sprint-start analysis app that focuses on the first three steps of acceleration.

The current product shape assumes:

- frontend and user experience stay as they are
- backend API and analysis logic stay intact
- uploaded videos are treated as temporary files
- result data is kept, but source videos are deleted after analysis

That lets us keep the current analysis precision while moving to a more predictable fixed-cost VPS setup.

## Stack

- Frontend: Next.js App Router + Tailwind CSS
- Backend API: FastAPI
- Analysis worker: Python worker process using the existing analysis pipeline
- Database: PostgreSQL
- Reverse proxy: Caddy
- Temporary storage: local shared volume, deleted after analysis
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
  Caddyfile
  .env.production.example
```

## Recommended Production Shape

For the current launch phase, the safest setup is a single fixed-cost VPS with five services:

- `caddy`: HTTPS and domain routing
- `frontend`: Next.js app
- `backend`: FastAPI API
- `worker`: analysis worker process
- `postgres`: relational database

The frontend, API, and worker stay logically separate, but live on one server to keep cost simple.

### Request / Analysis Flow

1. The user uploads a video from the current UI.
2. The backend stores the video in a temporary shared volume.
3. The backend creates an analysis row with `queued`.
4. The worker picks up the queued job and runs the current analysis logic unchanged.
5. The result payload is saved to PostgreSQL.
6. The temporary source video is deleted.
7. The frontend reads only the stored result data.

This means:

- analysis precision is not reduced
- UI can stay the same
- disk usage stays under control because videos are not archived indefinitely

## Local Development

### 1. Start PostgreSQL only

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai
docker compose up -d postgres
```

### 2. Run the backend locally

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### 3. Run the frontend locally

```bash
cd /Users/hayashikeita/Documents/New\ project/start-ai/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

## VPS Deployment

### 1. Prepare the server

Recommended starting point:

- Ubuntu 22.04 or 24.04
- 2 vCPU / 4 GB RAM minimum
- 4 vCPU / 8 GB RAM if you want more comfortable headroom

Install:

- Docker
- Docker Compose plugin

### 2. Copy the project to the server

Example target:

```bash
/opt/start-ai
```

### 3. Create the production env file

```bash
cd /opt/start-ai
cp .env.production.example .env.production
```

Then set at least:

- `APP_DOMAIN`
- `API_DOMAIN`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `INTERNAL_WORKER_TOKEN`

### 4. Start the stack

```bash
docker compose --env-file .env.production up -d --build
```

### 5. Verify services

Check:

```bash
docker compose ps
docker compose logs backend --tail=100
docker compose logs worker --tail=100
```

Health endpoint:

```bash
curl https://api.your-domain.example/api/v1/health
```

## Docker Compose Services

The included [docker-compose.yml](/Users/hayashikeita/Documents/New%20project/start-ai/docker-compose.yml) is designed for this launch-phase VPS setup.

### Services

- `caddy`
  - terminates HTTPS
  - routes `APP_DOMAIN` to `frontend`
  - routes `API_DOMAIN` to `backend`

- `frontend`
  - serves the current Next.js UI
  - talks to backend internally through `INTERNAL_API_BASE_URL`

- `backend`
  - exposes API routes
  - writes uploaded videos to `/app/uploads_tmp`
  - does not run the embedded worker

- `worker`
  - runs analysis jobs
  - reads the same `/app/uploads_tmp` volume
  - writes only result data to PostgreSQL

- `postgres`
  - stores users, analyses, and result payloads

### Shared volumes

- `uploads_tmp`
  - shared only by `backend` and `worker`
  - source videos live here temporarily

- `postgres_data`
  - database persistence

## Video Retention Policy

The recommended policy is:

- upload video
- analyze
- save result payload
- delete source video immediately on success

And for failures:

- keep failed source files only briefly
- delete them during cleanup / retry recovery

This keeps the system closer to fixed-cost operation.

## Environment Files

### Root production env

Use [/.env.production.example](/Users/hayashikeita/Documents/New%20project/start-ai/.env.production.example) as the base for VPS deployment.

### Backend env

Use [/Users/hayashikeita/Documents/New project/start-ai/backend/.env.example](/Users/hayashikeita/Documents/New%20project/start-ai/backend/.env.example) for local backend runs and reference values.

### Frontend env

Use [/Users/hayashikeita/Documents/New project/start-ai/frontend/.env.local.example](/Users/hayashikeita/Documents/New%20project/start-ai/frontend/.env.local.example) for local frontend development.

## What This Setup Intentionally Does Not Change

To protect analysis quality, this migration does **not** change:

- pose extraction logic
- event detection logic
- scoring logic
- feedback generation rules

The purpose of this VPS move is operational stability and predictable cost, not model simplification.

## Launch Checklist

Before launch, confirm:

1. login works on desktop and mobile
2. upload works on desktop and mobile
3. queued jobs move to completed
4. result pages load correctly
5. dashboard shows user-specific history
6. source videos are deleted after successful analysis
7. old failed uploads are cleaned up
8. backend and worker recover after restart

## Next Upgrade Path

When usage grows, scale in this order:

1. keep frontend as-is
2. move worker to its own VPS
3. move PostgreSQL to a managed service
4. move temporary upload storage to S3-compatible storage if needed

That path keeps the current analysis precision while giving more room for traffic.

# Backend guide

The backend provides the FastAPI API, Clerk authentication, quality gate, Celery jobs, MediaPipe and Librosa analysis, OpenAI transcription/coaching, and Supabase persistence.

Run commands in `backend/` unless stated otherwise.

## Setup

Requirements: Python 3.11, FFmpeg/ffprobe, Redis, and a configured `.env`.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Required configuration:

| Variable | Purpose |
| --- | --- |
| `ITSPEAK_REDIS_URL` | Celery broker and result backend |
| `ITSPEAK_FRONTEND_ORIGIN` | Exact allowed frontend origin |
| `CLERK_SECRET_KEY` | Clerk token verification |
| `ITSPEAK_SUPABASE_URL` | Supabase project |
| `ITSPEAK_SUPABASE_SECRET_KEY` | Server-only database and Storage access |
| `ITSPEAK_OPENAI_API_KEY` | Whisper transcription and generated coaching |
| `ITSPEAK_ARTIFACT_DIR` | Pending upload directory |

Optional settings, thresholds, and safe defaults are documented in `.env.example`.

## Run

From the repository root:

```bash
npm run backend
```

This starts or reuses Redis, then runs FastAPI, one solo Celery worker, and Celery Beat. Useful endpoints:

- Health: `http://localhost:8000/healthz`
- OpenAPI UI: `http://localhost:8000/docs`

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET/POST` | `/projects` | List or create projects |
| `GET/PATCH/DELETE` | `/projects/{id}` | Manage one project |
| `GET` | `/projects/{id}/sessions` | List retained sessions |
| `POST` | `/sessions` | Upload a video and start analysis |
| `GET` | `/sessions/{id}` | Read processing state or results |
| `POST` | `/sessions/{id}/confirm` | Continue after quality warnings |
| `PATCH` | `/sessions/{id}/transcript` | Save a corrected transcript |
| `GET` | `/sessions/{id}/artifacts` | Create signed artifact URLs |
| `GET` | `/archetypes` | List archetypes |
| `GET` | `/healthz` | Readiness check |

Authenticated routes use the Clerk user ID as the ownership boundary.

## Persistence

- `persistence/schema.sql` bootstraps a new empty Supabase project.
- `../supabase/migrations/` is the ordered CLI and upgrade path.
- Successful reports and private artifacts are committed to Supabase.
- Session 1 is the protected baseline; each project retains up to five successful sessions.
- Temporary local artifacts expire after 24 hours.

## Production container

Build from the repository root:

```bash
docker build --platform linux/amd64 -t itspeak-backend ./backend
```

Deploy `backend/Dockerfile` with:

- a managed persistent Redis URL;
- a persistent volume mounted at `/data`;
- `ITSPEAK_ENVIRONMENT=production`;
- `ITSPEAK_ARTIFACT_DIR=/data/itspeak-sessions`;
- `CELERY_WORKER_CONCURRENCY=1`;
- exactly one application replica;
- health check `/healthz`.

FastAPI, Celery, and Beat share pending files, so they must remain in the same service until uploads are staged in shared object storage.

The worker uses Celery's `solo` pool. After every full analysis it schedules a graceful worker shutdown; Supervisor immediately starts a clean worker to reclaim native MediaPipe and Librosa memory. Redis late acknowledgements protect interrupted jobs.

Librosa's Numba cache is stored under the artifact volume to avoid recompilation across deployments.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

If jobs remain queued, confirm Redis is reachable and the logs contain `celery@... ready`. If analysis fails, check FFmpeg availability and server-side Clerk, Supabase, and OpenAI configuration without printing their values.

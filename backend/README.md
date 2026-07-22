# Backend

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set the required values in `.env`, including `ITSPEAK_OPENAI_API_KEY` for live
transcription and generated coaching. Then start the complete backend from this
folder with one command:

```bash
node ../scripts/run-backend.mjs
```

This starts and supervises FastAPI at `http://127.0.0.1:8000`, the Celery
analysis worker, the Celery cleanup scheduler, and Redis in the same terminal.
If the configured Redis instance is already running, it is reused. Otherwise,
the command starts a local Redis process. Wait for `Application startup
complete` and `celery@... ready` before using the app.

Press `Ctrl+C` once to stop the complete backend. The supervisor stops the API,
worker, scheduler, and any Redis process that it started; it does not stop a
Redis instance that was already running.

Node.js, `redis-server`, `redis-cli`, `ffmpeg`, and `ffprobe` must be available
on `PATH`. The Python services are run through this folder's `.venv`.

For service-specific debugging only, the components can still be started in
separate terminals:

```bash
redis-server
.venv/bin/python -m celery -A itspeak.celery_app.celery_app worker --loglevel=info --pool=solo
.venv/bin/python -m celery -A itspeak.celery_app.celery_app beat --loglevel=info
.venv/bin/python -m uvicorn itspeak.api:app --reload
```

The persistence API is:

- `GET/POST /projects` — list and create owned projects.
- `GET/PATCH/DELETE /projects/{id}` — read, edit, or remove an owned project.
- `GET /projects/{id}/sessions` — list retained project sessions.
- `POST /sessions` — private upload and quality-gate start.
- `GET /sessions/{id}` — authenticated gate/job/report state.
- `POST /sessions/{id}/confirm` — authenticated warning override.
- `GET /sessions/{id}/artifacts` — short-lived signed playback and landmarks.

The older token-based `/video` and `/landmarks` routes remain for temporary
session compatibility, but the persisted frontend uses signed Storage URLs.

Pending session artifacts use opaque names outside the webroot and expire after
24 hours. Successful reports and artifacts are committed to Supabase Postgres
and private Storage. Run Celery beat for temporary and retryable object cleanup.
The authoritative migration is under `../supabase/migrations` and
`persistence/schema.sql` is the matching SQL Editor snapshot.

When annotated fixture clips are available, validate the provisional cadence
and record three-minute runtime with:

```bash
python scripts/validate_cadence.py tests/fixtures/*.mp4
```

The command fails if 5 fps changes the movement class or differs from 10 fps by
more than five percentage points on any available aggregate metric.

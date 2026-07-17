# Backend

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `ITSPEAK_OPENAI_API_KEY`, then run Redis, the worker, and API from this folder:

```bash
redis-server
celery -A itspeak.celery_app.celery_app worker --loglevel=info
celery -A itspeak.celery_app.celery_app beat --loglevel=info
uvicorn itspeak.api:app --reload
```

`ffmpeg` and `ffprobe` must be available on PATH. The persistence API is:

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

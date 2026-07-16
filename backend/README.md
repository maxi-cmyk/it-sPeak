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

`ffmpeg` and `ffprobe` must be available on PATH. The session API is:

- `POST /sessions` — private upload and quality-gate start.
- `GET /sessions/{id}` — authenticated gate/job/report state.
- `POST /sessions/{id}/confirm` — authenticated warning override.
- `GET /sessions/{id}/video` — authenticated byte-range playback.
- `GET /sessions/{id}/landmarks` — authenticated gzip landmark artifact.

Session artifacts use opaque names outside the webroot and expire after 24
hours. Run Celery beat for hourly cleanup. Production storage and database ports
remain scaffolded in `itspeak/persistence.py` and `persistence/schema.sql`.

When annotated fixture clips are available, validate the provisional cadence
and record three-minute runtime with:

```bash
python scripts/validate_cadence.py tests/fixtures/*.mp4
```

The command fails if 5 fps changes the movement class or differs from 10 fps by
more than five percentage points on any available aggregate metric.

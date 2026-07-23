# Backend operational guide

The backend contains the FastAPI surface, Clerk authentication boundary, quality gate, Celery jobs, MediaPipe and Librosa analysis, OpenAI transcription/coaching, and Supabase persistence.

Run every command in this guide from `backend/` unless stated otherwise. For system prerequisites, dependency installation, environment creation, and Supabase migration setup, start with the [root README](../README.md).

## Requirements

- Node.js 20+ for the single-command service supervisor.
- Python 3.11 and `backend/.venv` with `requirements.txt` installed.
- FFmpeg and ffprobe on `PATH`, or configured through `ITSPEAK_FFMPEG_BIN` and `ITSPEAK_FFPROBE_BIN`.
- Redis available locally or through `ITSPEAK_REDIS_URL`.
- A configured `backend/.env` containing Clerk, Supabase, and OpenAI values.

## Environment variables

The complete defaults and calibration values are documented in `.env.example`. The operationally important values are:

| Variable | Requirement | Purpose |
| --- | --- | --- |
| `ITSPEAK_FRONTEND_ORIGIN` | Required | Exact allowed browser origin |
| `CLERK_SECRET_KEY` | Required | Clerk session-token verification |
| `CLERK_JWT_KEY` | Optional | Local PEM verification; otherwise Clerk JWKS is used |
| `ITSPEAK_SUPABASE_URL` | Required | Supabase project URL |
| `ITSPEAK_SUPABASE_SECRET_KEY` | Required | Backend-only Postgres and Storage access |
| `ITSPEAK_SUPABASE_STORAGE_BUCKET` | Optional | Private artifact bucket; defaults to `session-artifacts` |
| `ITSPEAK_REDIS_URL` | Required service | Celery broker; defaults to `redis://localhost:6379/0` |
| `ITSPEAK_OPENAI_API_KEY` | Required for full analysis | Whisper transcription and generated coaching |
| `ITSPEAK_ARTIFACT_DIR` | Platform-dependent | Pending local artifacts; use a Windows path on Windows |

FastAPI also accepts `ITSPEAK_CLERK_SECRET_KEY` and `ITSPEAK_CLERK_JWT_KEY` as aliases. Never expose the Clerk or Supabase secret through a frontend `NEXT_PUBLIC_*` variable.

## Run the complete backend

Start FastAPI, the Celery worker, Celery Beat, and Redis in one terminal:

```bash
node ../scripts/run-backend.mjs
```

The supervisor:

- reuses the Redis instance configured by `ITSPEAK_REDIS_URL` when it responds;
- starts a local `redis-server` when the configured local instance is unavailable;
- starts FastAPI at `http://127.0.0.1:8000`;
- starts the analysis worker with the solo pool;
- starts the cleanup scheduler;
- stops every service it started when `Ctrl+C` is pressed;
- leaves a Redis instance that was already running untouched.

The backend is ready when the logs include both:

```text
Application startup complete
celery@... ready
```

The API health endpoint is [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz), and interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Running services individually

Use separate services only when isolating a failure. Normal development should use the supervisor above.

### macOS/Linux

Terminal 1 — Redis, when no Redis service is already running:

```bash
redis-server
```

Terminal 2 — FastAPI:

```bash
MPLCONFIGDIR=/tmp/itspeak-matplotlib .venv/bin/python \
  -m uvicorn itspeak.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 3 — Celery worker:

```bash
MPLCONFIGDIR=/tmp/itspeak-matplotlib .venv/bin/python \
  -m celery -A itspeak.celery_app.celery_app \
  worker --loglevel=info --pool=solo
```

Terminal 4 — Celery Beat cleanup scheduler:

```bash
.venv/bin/python -m celery -A itspeak.celery_app.celery_app \
  beat --loglevel=info
```

Stop each foreground service with `Ctrl+C`.

### Windows PowerShell

Start or reuse a Redis-compatible service. With the Docker container from the root setup:

```powershell
docker start itspeak-redis
```

Terminal 1 — FastAPI:

```powershell
$env:MPLCONFIGDIR = "$env:TEMP\itspeak-matplotlib"
.\.venv\Scripts\python.exe -m uvicorn itspeak.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 — Celery worker:

```powershell
$env:MPLCONFIGDIR = "$env:TEMP\itspeak-matplotlib"
.\.venv\Scripts\python.exe -m celery -A itspeak.celery_app.celery_app worker --loglevel=info --pool=solo
```

Terminal 3 — Celery Beat cleanup scheduler:

```powershell
.\.venv\Scripts\python.exe -m celery -A itspeak.celery_app.celery_app beat --loglevel=info
```

The solo pool is required for the documented Windows worker configuration.

## Diagnostics

### Confirm executables and Python dependencies

macOS/Linux:

```bash
node --version
.venv/bin/python --version
ffmpeg -version
ffprobe -version
redis-server --version
.venv/bin/python -c "import celery, fastapi, librosa, mediapipe; print('Python dependencies OK')"
```

Windows PowerShell:

```powershell
node --version
.\.venv\Scripts\python.exe --version
ffmpeg -version
ffprobe -version
.\.venv\Scripts\python.exe -c "import celery, fastapi, librosa, mediapipe; print('Python dependencies OK')"
```

If the import check fails, reinstall the locked backend requirements:

macOS/Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Check configuration without printing secrets

macOS/Linux:

```bash
.venv/bin/python -c "from itspeak.settings import get_settings; s=get_settings(); print({'redis': bool(s.redis_url), 'clerk': bool(s.clerk_secret_key), 'supabase': s.supabase_configured, 'openai': bool(s.openai_api_key)})"
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from itspeak.settings import get_settings; s=get_settings(); print({'redis': bool(s.redis_url), 'clerk': bool(s.clerk_secret_key), 'supabase': s.supabase_configured, 'openai': bool(s.openai_api_key)})"
```

Every value should be `True` for the complete persisted analysis flow.

### Check FastAPI

macOS/Linux:

```bash
curl --fail http://127.0.0.1:8000/healthz
```

Windows PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

### Check Redis

Local Redis on macOS/Linux:

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

Docker Redis on Windows:

```powershell
docker exec itspeak-redis redis-cli ping
```

The expected response is `PONG`.

### Check the Celery worker

macOS/Linux:

```bash
.venv/bin/python -m celery -A itspeak.celery_app.celery_app inspect ping
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m celery -A itspeak.celery_app.celery_app inspect ping
```

Run this while the worker is active. A healthy worker returns a `pong` response.

### Find port conflicts

macOS/Linux:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:6379 -sTCP:LISTEN
```

Windows PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Get-NetTCPConnection -LocalPort 6379 -State Listen
```

### Run backend tests

Complete suite on macOS/Linux:

```bash
MPLCONFIGDIR=/tmp/itspeak-matplotlib .venv/bin/python \
  -m unittest discover -s tests -p 'test_*.py' -v
```

Complete suite on Windows PowerShell:

```powershell
$env:MPLCONFIGDIR = "$env:TEMP\itspeak-matplotlib"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Target one subsystem on macOS/Linux:

```bash
.venv/bin/python -m unittest tests.test_auth_boundary -v
.venv/bin/python -m unittest tests.test_persistence_foundation -v
.venv/bin/python -m unittest tests.test_improvement_focus -v
.venv/bin/python -m unittest tests.test_quality_metrics -v
```

Use `.\.venv\Scripts\python.exe` in place of `.venv/bin/python` for the same targeted commands on Windows.

### Validate analysis cadence

When annotated fixture videos exist under `tests/fixtures/`:

macOS/Linux:

```bash
.venv/bin/python scripts/validate_cadence.py tests/fixtures/*.mp4
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/validate_cadence.py tests/fixtures/*.mp4
```

The command fails when the provisional 5 fps cadence changes the movement classification or differs from the 10 fps reference by more than five percentage points on an available aggregate metric.

## Common failures

| Symptom | Likely cause | Recovery |
| --- | --- | --- |
| Supervisor reports that the virtual environment is missing | `backend/.venv` was not created | Follow the root installation steps |
| Redis does not become ready | Redis executable missing, custom Redis unreachable, or port conflict | Run the Redis and port checks above |
| API starts but jobs remain queued | Celery worker is not connected to the same Redis URL | Compare `ITSPEAK_REDIS_URL` and run `inspect ping` |
| Authentication returns `401` | Missing session, mismatched Clerk instances, or invalid token | Reauthenticate and compare frontend/backend Clerk configuration |
| Authentication returns `503` | Clerk verification is not configured or unavailable | Check the Clerk configuration result and backend logs |
| Persistence requests fail | Supabase URL/secret missing, schema not migrated, or bucket unavailable | Confirm configuration, apply migrations, and inspect Supabase |
| Analysis fails during media probing | FFmpeg or ffprobe missing or not configured | Run version checks or set the explicit binary paths |
| Analysis fails at transcription | OpenAI key missing or rejected | Check `ITSPEAK_OPENAI_API_KEY` without printing it |
| Matplotlib reports an unwritable cache | Default cache directory is restricted | Set `MPLCONFIGDIR` as shown in the service commands |

## API surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET/POST` | `/projects` | List or create owned projects |
| `GET/PATCH/DELETE` | `/projects/{project_id}` | Read, edit, or delete an owned project |
| `GET` | `/projects/{project_id}/sessions` | List retained sessions |
| `POST` | `/sessions` | Upload a private recording and start the quality gate |
| `GET` | `/sessions/{session_id}` | Read quality, job, and report state |
| `POST` | `/sessions/{session_id}/confirm` | Continue after warning-level quality findings |
| `PATCH` | `/sessions/{session_id}/transcript` | Save a corrected transcript |
| `GET` | `/sessions/{session_id}/artifacts` | Create short-lived signed artifact URLs |
| `GET` | `/sessions/{session_id}/video` | Stream temporary authenticated video with byte ranges |
| `GET` | `/sessions/{session_id}/landmarks` | Read temporary gzip landmarks |
| `GET` | `/archetypes` | List archetype availability |
| `GET` | `/healthz` | Readiness check |

`POST /sessions/analyze` remains temporarily as a deprecated compatibility alias for `POST /sessions`.

## Persistence and artifact lifecycle

- `persistence/schema.sql` is the consolidated master schema for a new empty project and must be run only once.
- Timestamped files under `../supabase/migrations/` are retained as the non-destructive upgrade path for existing databases.
- Pending and failed session artifacts use opaque local paths and expire after 24 hours.
- Successful reports, videos, and landmarks are committed to Supabase Postgres and private Storage.
- Signed artifact URLs are short-lived and owner-authorized.
- Celery Beat must run so temporary and retryable artifacts are cleaned up.

## Related documentation

- [Project setup and prerequisites](../README.md)
- [Frontend operational guide](../frontend/README.md)

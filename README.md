# it'sPEAK

AI-powered public speaking coach. Upload a talk, get archetype-calibrated
delivery scores and tactical, grounded coaching cards.

## Architecture

The core is split into three strictly-decoupled layers that only communicate
through the Pydantic contracts in `itspeak/models.py`:

```
  ffmpeg (2 fps)        Face + Body (parallel)      archetype calibration        low-temp LLM
  ─────────────  ──►    ──────────────────────  ──►  ─────────────────────  ──►  ─────────────
  extract_frames        analyze_frames()             normalize_scores()          CoachingService
  pipeline.py           pipeline.py                  config.py                   coaching.py
        │                      │                            │                          │
        └── FrameBatch ────────┴── VideoAnalysisResult ─────┴── NormalizedScores ──────┴── list[CoachingCard]
```

| File | Responsibility |
|------|----------------|
| `itspeak/models.py`   | Shared Pydantic contracts (the only cross-layer coupling). |
| `itspeak/pipeline.py` | FastAPI endpoints, Celery task, ffmpeg extraction, MediaPipe analysis loops. |
| `itspeak/config.py`   | Archetype presets + raw-metric → 0-100 normalization. |
| `itspeak/coaching.py` | LLM prompt assembly, provider calls, JSON validation, fallback. |
| `itspeak/celery_app.py` / `settings.py` | Celery/Redis wiring and env-driven settings. |

### Design decisions mapped to requirements

- **~93% CPU reduction**: `ffmpeg` samples at **2 fps** (from ~30 fps) before any
  inference runs. Frames are also downscaled (`ITSPEAK_MAX_FRAME_WIDTH`).
- **Parallel modules**: `analyze_frames()` runs Face Mesh and BlazePose in a
  2-thread `ThreadPoolExecutor`; MediaPipe's C++ inference releases the GIL, so
  they truly run concurrently.
- **No RAG**: `coaching.py` uses zero-/few-shot structured prompting at
  temperature `0.3` with hard JSON + anti-hallucination constraints.
- **Modular contracts**: layers never import each other's internals — only
  `models.py`.
- **Graceful degradation**: missing faces / low-confidence tracking / short
  clips log warnings and emit neutral fallback scores (and a rule-based coaching
  fallback if the LLM is unavailable) instead of crashing.

## Setup

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env    # then fill in your LLM API key
```

You also need the **ffmpeg** and **ffprobe** binaries on `PATH` (or set
`ITSPEAK_FFMPEG_BIN` / `ITSPEAK_FFPROBE_BIN`) and a running **Redis** instance.

## Run

```bash
# 1) Redis (example via Docker)
docker run -p 6379:6379 redis:7

# 2) Celery worker (does the CV + LLM work)
celery -A itspeak.celery_app.celery_app worker --loglevel=info

# 3) API
uvicorn itspeak.pipeline:app --reload
```

## Usage

```bash
# enqueue
curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{
  "video_path": "/abs/path/to/talk.mp4",
  "archetype": "motivational_keynote",
  "audience_context": "A 500-person startup conference keynote about resilience."
}'
# -> {"task_id": "...", "status": "queued"}

# poll
curl http://localhost:8000/result/<task_id>
```

Archetypes: `corporate_board`, `motivational_keynote`.

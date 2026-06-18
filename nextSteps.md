# Next Steps

## Recommendation
The audio prototype does not need more standalone scoring refinement before product integration. The current calibration/evaluator pass ranks all populated voice-testing folders correctly with `ranking failures: 0` and `warnings: 0`.

Move the prototype into the full `it'sPEAK` product as the first production analysis module. Keep future tuning data-driven: only change scoring weights or thresholds when a new holdout set exposes a specific failure.

## Product PRD Target
Build an on-demand public speaking coach for university students that accepts up to 3-minute English-language presentation videos and returns actionable feedback across:
- Tonal & vocal analysis
- Facial presence analysis
- Body language analysis
- Speaking archetypes
- LLM coaching cards
- Project folders and progress tracking

## Scope
- In: product integration, backend job pipeline, frontend upload/results flow, project/session persistence, audio module migration, quality gate, and product-level regression tests.
- Out for this phase: paid billing, team collaboration, native mobile app, production deployment hardening, and model training.

## Current Prototype Baseline
- [x] Segment-level audio feedback exists in `audio-engine.py`.
- [x] Per-segment WPM, fillers, pause gaps, and pitch variation are computed.
- [x] Segment-specific `speech_issues` replace generic first-phrase flags.
- [x] Calibration stats include segment issue counts.
- [x] Unit tests cover segment splitting, segment issue flags, and holdout evaluator behavior.
- [x] Voice-testing pipeline was rerun for populated folders.

## Integration Action Items In Sequence

### 1. Create Product App Skeleton
- [ ] Create a `backend/` FastAPI app with health check, app config, and test runner.
- [ ] Create a `frontend/` React + TypeScript + Tailwind app.
- [ ] Add a root README section documenting local startup commands for backend and frontend.
- [ ] Add CI-style verification commands for Python tests and frontend type/lint checks.

### 2. Turn The Audio Prototype Into An Importable Module
- [ ] Move analysis logic out of `audio-engine.py` into an importable backend package, for example `backend/app/analysis/audio.py`.
- [ ] Keep `audio-engine.py` as a CLI wrapper that calls the shared module.
- [ ] Preserve the current JSON result shape so existing calibration fixtures remain useful.
- [ ] Add tests proving CLI output and backend module output match for mocked audio inputs.

### 3. Add Upload And Analysis Job API
- [ ] Implement `POST /projects/{project_id}/sessions` to create an analysis session record.
- [ ] Implement `POST /sessions/{session_id}/upload-url` as the future R2 presigned-upload boundary.
- [ ] Implement `POST /sessions/{session_id}/analyze` to enqueue analysis work.
- [ ] For local development, support filesystem-backed uploads before wiring Cloudflare R2.
- [ ] Return stable job states: `queued`, `processing`, `complete`, `failed`.

### 4. Add Persistence Model
- [ ] Define Supabase-compatible tables for users, projects, sessions, analysis results, coaching cards, and retained video keys.
- [ ] Enforce the PRD rule: maximum 5 sessions per project.
- [ ] Protect Session 1 as the calibration baseline unless the project is explicitly reset.
- [ ] Store archetype switches on sessions so cross-archetype comparisons can be marked non-normalised.
- [ ] Add tests for 5-session deletion selection and Session 1 protection.

### 5. Implement Speaking Archetypes
- [ ] Add the 6 preset archetypes: Corporate/Board, Startup Pitch, Academic/Conference, Informal/Team, Motivational/Keynote, and Job Interview.
- [ ] Add Custom mode with audience size, formality, domain, and free-text context capped at 300 characters.
- [ ] Implement the 5-10 question rule-based onboarding quiz that recommends the closest preset.
- [ ] Feed archetype thresholds into pause and scoring configuration without hardcoding one global target.
- [ ] Add tests for quiz classification and custom-context validation.

### 6. Add Pre-Analysis Quality Gate
- [ ] Check audio signal level before transcription and return actionable re-recording guidance when too quiet.
- [ ] Add video duration validation with a hard 3-minute limit.
- [ ] Add placeholder interfaces for face confidence and primary-speaker detection so the API contract is ready before MediaPipe is integrated.
- [ ] Surface quality-gate warnings before full analysis starts.

### 7. Build Initial Frontend Workflow
- [ ] Build project list, project detail, and new project screens.
- [ ] Build upload flow with archetype selection before analysis.
- [ ] Build job status polling for queued/processing/complete/failed states.
- [ ] Build results dashboard tabs for Vocal, Face, Body, Transcript, and Coaching.
- [ ] Render the current audio prototype output in the Vocal and Transcript tabs first.

### 8. Add LLM Coaching Cards
- [ ] Create a structured coaching-card schema: module, problem, why it matters, concrete action, source metric, and severity.
- [ ] Generate up to 3 cards per module from analysis metrics.
- [ ] Add previous-session rotation guard so repeated advice is suppressed unless stagnation is detected.
- [ ] Add stagnation override when a metric is unchanged across 3+ consecutive sessions.
- [ ] Add tests using mocked OpenAI responses and deterministic fallback cards.

### 9. Add Facial Presence Analysis
- [ ] Integrate MediaPipe FaceLandmarker for sampled video frames.
- [ ] Compute eye contact ratio, expression variation, smile naturalness, and head movement stability.
- [ ] Store frame-indexed face landmark JSON for client-side overlays.
- [ ] Add low-confidence flags rather than silently scoring unreliable face metrics.
- [ ] Build client-side face mesh overlay and eye-contact timeline heatmap.

### 10. Add Body Language Analysis
- [ ] Integrate MediaPipe PoseLandmarker for sampled video frames.
- [ ] Compute posture alignment, shoulder symmetry, gesture frequency/range, movement purposefulness, and spatial use.
- [ ] Store frame-indexed pose landmark JSON for client-side skeleton overlays.
- [ ] Flag partial visibility when pose confidence is too low for reliable scoring.
- [ ] Add result cards that distinguish low-confidence metrics from poor performance.

### 11. Add Progress Tracking
- [ ] Use Session 1 as project calibration baseline.
- [ ] Compute deltas vs previous session and vs Session 1.
- [ ] Build radar chart across Vocal, Face, and Body scores.
- [ ] Annotate sessions recorded under different archetypes as non-normalised.
- [ ] Add Best Session Replay per dimension using retained original video.
- [ ] Add Coaching Playbook from saved coaching cards.

### 12. Product-Level Verification
- [ ] Keep `python3 -m unittest discover -s tests` green for prototype compatibility.
- [ ] Add backend API tests for session lifecycle, job state transitions, and analysis persistence.
- [ ] Add frontend tests for upload, job polling, and rendering analysis results.
- [ ] Run the voice-testing pipeline after audio module migration and confirm evaluator output still reports `ranking failures: 0`.
- [ ] When `voice-testing4` contains recordings, add it to `calibration_manifest.json` and run it as a holdout check before changing scoring thresholds.


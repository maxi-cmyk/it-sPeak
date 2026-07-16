# Frontend

## Setup

```bash
npm ci
cp .env.example .env.local
npm run dev
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`.

The session flow is implemented in three layers:

- `lib/api.js` owns authenticated session, confirmation, video, and artifact calls.
- `hooks/useAnalysisJob.js` owns quality-gate and analysis polling state.
- `VideoAnalysisPlayer.js` owns synchronized overlays and the seekable heatmap.
- Components and pages render pass, confirmation, rejection, progress, and report states.

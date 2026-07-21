# Frontend

## Setup

```bash
npm ci
cp .env.example .env.local
npm run dev
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`.

The persisted project and session flow is implemented in three layers:

- `lib/api.js` owns project CRUD, session upload/polling, and signed artifact calls.
- `hooks/useAnalysisJob.js` owns quality-gate and analysis polling state.
- `VideoAnalysisPlayer.js` owns synchronized overlays and the seekable heatmap.
- Components and pages render loading/error/empty states, five-session replacement,
  quality decisions, progress, and durable reports.

The frontend obtains a short-lived Clerk session token for every FastAPI request.
FastAPI verifies that token and uses its `sub` claim as the Supabase owner ID;
the browser never receives the Supabase secret key.

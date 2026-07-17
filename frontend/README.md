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

Until Clerk is connected, the backend supplies the explicit development owner
configured by `ITSPEAK_DEV_USER_ID`; the browser never receives the Supabase
secret key.

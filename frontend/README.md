# Frontend guide

The frontend is a Next.js application for projects, uploads, processing states, reports, progress charts, transcripts, and synchronized video overlays.

Run commands in `frontend/`.

## Setup

```bash
npm ci
cp .env.example .env.local
```

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | FastAPI base URL |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Public Clerk browser key |
| `CLERK_SECRET_KEY` | Server-only Clerk middleware key |

Both Clerk keys must belong to the same application used by the backend. Never expose a secret through `NEXT_PUBLIC_*`.

## Commands

```bash
npm run dev      # http://localhost:3000
npm test
npm run build
npm run start
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Project archive |
| `/project/{id}` | Sessions and progress |
| `/session/{id}` | Scores, coaching, transcript, and synchronized evidence |
| `/sign-in` | Clerk sign-in |
| `/sign-up` | Clerk registration |

Clerk protects application routes. API requests include a fresh Clerk bearer token; the browser accesses Supabase artifacts only through short-lived signed URLs returned by FastAPI.

## Vercel

Configure the project with:

- root directory: `frontend`;
- install command: `npm ci`;
- build command: `npm run build`;
- production branch: `main`;
- no custom output directory.

Set the three environment variables above with the production FastAPI URL and production Clerk keys. Add the Vercel domain to the Clerk production application so signed-out users can reach `/sign-in` and protected routes redirect correctly.

After deployment, verify:

```text
/sign-in                 opens while signed out
/                        redirects to sign-in while signed out
authenticated API calls  do not return 401 or CORS errors
```

If authentication fails, confirm both deployments use the same Clerk instance and that backend `ITSPEAK_FRONTEND_ORIGIN` exactly matches the Vercel origin.

## Key modules

- `lib/api.js`: authenticated API client.
- `hooks/useAnalysisJob.js`: upload, quality-gate, polling, and replacement state.
- `components/VideoAnalysisPlayer.js`: signed video, landmarks, overlays, and eye-contact timeline.

# Frontend operational guide

The frontend is a Next.js web application that renders projects, retained rehearsal sessions, upload and quality-gate states, coaching reports, charts, and synchronized video overlays.

Run every command in this guide from `frontend/` unless stated otherwise. For full-machine prerequisites and first-time installation, start with the [root README](../README.md).

## Responsibilities and data flow

- `lib/api.js` owns authenticated project CRUD, session upload and polling, transcript updates, and signed artifact requests.
- `hooks/useAnalysisJob.js` owns quality-gate and analysis job state.
- `components/VideoAnalysisPlayer.js` owns synchronized landmarks and the seekable eye-contact timeline.
- Clerk protects application routes and supplies a fresh short-lived token for each FastAPI request.
- The browser does not query Supabase directly and never receives the Supabase secret key.

## Requirements

- Node.js 20 or newer.
- npm and the committed `package-lock.json`.
- A configured `frontend/.env.local` (Clerk keys from the same instance as the backend; see the [root cloud-account checklist](../README.md#create-the-cloud-accounts)).
- The backend available at `NEXT_PUBLIC_API_URL` for authenticated application data.

## Install

```bash
npm ci
```

Create the local environment file if it does not exist:

macOS/Linux:

```bash
cp .env.example .env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

## Environment variables

| Variable | Requirement | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Recommended | FastAPI base URL; defaults to `http://localhost:8000` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Required | Public key used by Clerk in the browser |
| `CLERK_SECRET_KEY` | Required | Server-only key used by Next.js middleware |
| `NEXT_PUBLIC_SUPABASE_URL` | Not currently used | Reserved public Supabase value |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Not currently used | Reserved public Supabase value |

Use the publishable and secret Clerk keys from the same Clerk instance. Never rename a secret to use a `NEXT_PUBLIC_*` prefix.

## Commands

| Command | Purpose |
| --- | --- |
| `npm ci` | Install the exact locked dependency tree |
| `npm run dev` | Start the development server at `http://localhost:3000` |
| `npm test` | Run all frontend Node tests |
| `npm run build` | Create and validate an optimized production build |
| `npm run start` | Serve the previously generated production build |

## Development server

Start the backend in another terminal, then run:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Signed-out users are redirected to `/sign-in`; all other application routes require Clerk authentication.

Stop the development server with `Ctrl+C`.

## Production build

```bash
npm run build
npm run start
```

`npm run start` requires a successful `.next` production build and listens on port 3000 by default.

## Tests

Run the complete frontend test suite:

```bash
npm test
```

Run one test file directly when isolating a failure:

```bash
node --test tests/apiAuth.test.mjs
node --test tests/improvementFocus.test.mjs
node --test tests/overlayMath.test.mjs
node --test tests/persistenceUi.test.mjs
```

## Diagnostics

### Confirm the runtime and dependency tree

```bash
node --version
npm --version
npm ls --depth=0
```

Use Node.js 20 or newer. If dependencies are missing or invalid, restore the locked tree with:

```bash
npm ci
```

### Confirm the backend is reachable

macOS/Linux:

```bash
curl --fail http://127.0.0.1:8000/healthz
```

Windows PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
```

The expected response is `{"status":"ok"}`. If it fails, use the [backend diagnostics](../backend/README.md#diagnostics).

### Find a process already using port 3000

macOS/Linux:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

Windows PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen
```

Stop the conflicting process or run Next.js on another port:

```bash
npm run dev -- --port 3001
```

If the port changes, update `ITSPEAK_FRONTEND_ORIGIN` in `backend/.env` to the exact new origin and restart the backend.

### Validate a production-only failure

```bash
npm run build
```

This catches missing imports, server/client boundary errors, invalid route output, and environment failures that development mode may not expose.

### Clear only the generated Next.js cache

Use this when stale compiled output persists after source changes. It does not remove dependencies or source files.

macOS/Linux:

```bash
rm -rf .next
npm run dev
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force .next
npm run dev
```

### Diagnose Clerk authentication

First-time Clerk setup (creating the app and allowing `http://localhost:3000` / `/sign-in` / `/sign-up`) is covered in the [root README](../README.md#create-the-cloud-accounts).

1. Confirm `.env.local` exists.
2. Confirm `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are populated without printing or sharing their values.
3. Confirm both keys belong to the same Clerk instance as `backend/.env`.
4. Confirm the backend uses that matching Clerk instance and that `ITSPEAK_FRONTEND_ORIGIN` exactly matches the browser origin (including port).
5. Restart the frontend after changing environment values.

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Redirect loop at sign-in | Missing or mismatched Clerk keys | Recheck both Clerk variables and restart Next.js |
| Every API request returns `401` | No active Clerk session or mismatched instances | Sign in again and compare frontend/backend Clerk instances |
| API returns `503` for authentication | Backend Clerk verification is not configured | Check `CLERK_SECRET_KEY` in `backend/.env` |
| Browser reports a CORS error | Frontend origin differs from backend configuration | Correct `ITSPEAK_FRONTEND_ORIGIN` and restart the backend |
| Project or session requests fail | Backend, Redis, or persistence is unavailable | Check `/healthz`, backend logs, and the backend operational guide |
| Styling or route output looks stale | Generated `.next` cache is stale | Remove only `.next` and restart development mode |

## Related documentation

- [Project setup and prerequisites](../README.md)
- [Backend operational guide](../backend/README.md)

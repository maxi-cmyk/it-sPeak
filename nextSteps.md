# Next Steps

This roadmap takes the project from parallel frontend prototyping to a stable school-project deployment. Deployment work starts only after the preferred frontend prototype has been accepted.

## Deployment branch decision

Use `main` as the production branch. This is the simplest and recommended setup for this project: prototype branches remain isolated and can use preview deployments, while merging an accepted version into `main` triggers the production deployment. A separate release branch would add process without providing much value for a school project.

## Phase 1 — Finish parallel frontend prototyping

**Status: In progress**

- Continue frontend iteration on the prototype branches while keeping `main` stable.
- Complete the intended interface and interaction flows before adding production deployment configuration.
- Test the prototype against the complete backend running locally.
- Run the frontend tests and production build, then complete a manual review of the main user journeys.
- Select the final prototype and merge only the accepted frontend changes into `main`.

**Completion gate:** the preferred frontend is approved, its build and tests pass, and the core user journeys work against the local backend.

## Phase 2 — Prepare the backend deployment container

**Status: Not started**

- Add a production container configuration for FastAPI, Celery Worker, Celery Beat, FFmpeg/ffprobe, and the required Python dependencies.
- Configure FastAPI to listen on the deployment platform's host and port rather than only `127.0.0.1:8000`.
- Decide how the deployed services will connect to Redis and ensure queued work survives normal service restarts.
- Supply Clerk, Supabase, Redis, OpenAI, frontend-origin, and storage settings through deployment environment variables without committing secrets.
- Confirm the container exposes the health endpoint and can complete an analysis job from upload through persisted results.

**Completion gate:** the backend has a stable public HTTPS URL, its health check passes, and its API and background jobs work after a clean deployment and restart.

## Phase 3 — Configure Vercel and Clerk

**Status: Not started**

- Create the Vercel frontend project with `frontend/` as its root directory and `main` as its production branch.
- Set `NEXT_PUBLIC_API_URL` to the deployed backend HTTPS URL.
- Add the matching Clerk publishable and secret keys to the appropriate Vercel environments.
- Set the backend's allowed frontend origin to the exact Vercel or custom-domain origin.
- Use preview deployments for non-`main` branches and keep their Clerk and backend configuration separate from the production environment where necessary.
- Redeploy after the environment variables and domain configuration are finalized.

**Completion gate:** the deployed frontend signs users in successfully and makes authenticated requests to the deployed backend without CORS, origin, or mixed-content errors.

## Phase 4 — Final verification

**Status: Not started**

- Run the complete frontend and backend automated checks against the release candidate.
- Manually verify sign-up/sign-in, project creation and editing, session upload, analysis progress, results, retained sessions, and sign-out.
- Confirm Celery Worker and Celery Beat process queued work and recover after a restart.
- Confirm project and session data persist in Supabase and private artifacts remain accessible only through the intended authenticated flow.
- Check production logs for authentication, CORS, upload, job, FFmpeg, OpenAI, Redis, and persistence failures.
- Confirm no secret values are committed or exposed through frontend `NEXT_PUBLIC_*` variables.
- Record the final demo URL and complete one end-to-end demonstration from a clean browser session.

**Completion gate:** the deployed application completes the full rehearsal workflow reliably and is ready for manual school-project demonstration.

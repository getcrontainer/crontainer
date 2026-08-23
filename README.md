# Crontainer

Crontainer schedules Docker containers with cron. Django exposes the REST API and serves the compiled Vue single-page application with WhiteNoise.

## Run locally

Start the API:

```bash
uv sync
mkdir -p data
uv run python manage.py migrate
uv run python manage.py setup
uv run python manage.py runserver
```

Start the Vue frontend in another terminal:

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

Vite serves the frontend on `http://localhost:5173` and proxies `/api` requests to the Django API on port 8000.

For the production deployment, run `docker compose up --build`. A single container builds the Vue frontend, serves the SPA and its static assets through Django, and exposes the complete application on `http://localhost:9090`.

## API

The API uses cookie-based session authentication. Fetch `/api/auth/csrf/` before signing in with `POST /api/auth/login/`, then use `/api/auth/me/` to obtain the current user. The main resources are exposed at:

- `/api/health/` (public system health)
- `/api/schedules/`
- `/api/jobs/` (read-only)
- `/api/credentials/`
- `/api/users/`
- `/api/nodes/`

All non-API routes fall back to the Vue application so browser navigation and refreshes work with its client-side router.

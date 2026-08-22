# Crontainer

Crontainer schedules Docker containers with cron. The application is split into a Django REST Framework API and a separate Vue single-page application.

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

For the production-shaped stack, run `docker compose up --build`; nginx serves the SPA on `http://localhost:9090` and proxies `/api` to the API container.

## API

The API uses cookie-based session authentication. Fetch `/api/auth/csrf/` before signing in with `POST /api/auth/login/`, then use `/api/auth/me/` to obtain the current user. The main resources are exposed at:

- `/api/schedules/`
- `/api/jobs/` (read-only)
- `/api/credentials/`
- `/api/users/`
- `/api/nodes/`

The API has no server-rendered pages or Django templates.

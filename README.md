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

## Configuration

Crontainer reads configuration from process environment variables and from the `.env` file in the project root. Process environment variables take precedence over values in `.env`. List values such as hosts and trusted origins are comma-separated.

### Likely necessary for production

Review and explicitly configure these values before exposing Crontainer outside a local development environment.

| Variable | Default | Description |
| --- | --- | --- |
| `SESSION_KEY` | Development-only built-in value | Django secret key used to sign sessions and other security-sensitive data. Set this to a long, unique, random value in production. |
| `ALLOWED_HOSTS` | `*` | Comma-separated hostnames Django may serve, for example `localhost,crontainer.example.com`. Restrict this in production. |
| `CSRF_TRUSTED_ORIGINS` | Empty | Comma-separated full origins trusted for unsafe requests, for example `https://crontainer.example.com`. Include the scheme. |
| `ADMIN_USERNAME` | Unset | Username created or updated by `manage.py setup`. If either admin variable is unset, Crontainer falls back to `settings.toml`. |
| `ADMIN_PASSWORD` | Unset | Password assigned by `manage.py setup`. Because setup runs on every container start, this value resets the configured administrator's password. Never use the example `admin` password in production. |

### Development, debugging, and advanced overrides

The defaults below normally work with the supplied Compose deployment. Override them for local debugging, non-standard installations, remote Docker daemons, or custom health monitoring.

| Variable | Default | Description |
| --- | --- | --- |
| `DEBUG` | `False` | Enables Django debug mode. Keep this disabled in production. |
| `DATABASE_URL` | `sqlite:///data/db.sqlite3` | Database connection URL parsed by `django-environ`. The default stores SQLite data in `data/db.sqlite3`, which the Compose deployment persists in its data volume. Override this only when using another database location or backend. |
| `CRONTAB_PATH` | `/tmp/cron.d` | Directory containing generated `ct_<schedule-id>` cron definition files. The Compose deployment overrides this with `/etc/cron.d`. |
| `CRONJOB_CMD` | See below | Template used to write each cron definition. It must contain the `{cron_rule}` and `{schedule_id}` placeholders. |
| `CRON_PID_FILE` | `/run/crond.pid` | PID file inspected by the system-health check for the cron daemon. |
| `JOB_UPDATER_PID_FILE` | `/run/crontainer-update-history.pid` | PID file written by the container entrypoint and inspected by the system-health check for the job-history updater. |
| `HEALTH_DISK_PATH` | `<project>/data` | Filesystem path whose disk usage is reported by the system-health endpoint. This resolves to `/app/data` in the container. |
| `HEALTH_DISK_MAX_USED_PERCENT` | `80.0` | Disk-used percentage at or above which the system-health check becomes unhealthy. |
| `DJANGO_SETTINGS_MODULE` | `crontainer.settings` | Advanced Django runtime override. The management, ASGI, and WSGI entrypoints set this automatically when it is absent. |

The default cron command template is:

```text
{cron_rule}\troot\tcd /app && /app/.venv/bin/python /app/manage.py run_schedule {schedule_id}
```

Here, `\t` represents a tab in the generated cron file. If the application is installed outside the container, override `CRONJOB_CMD` so its working directory and Python executable point to that installation.

Example production-style configuration:

```dotenv
DEBUG=False
SESSION_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=crontainer.example.com
CSRF_TRUSTED_ORIGINS=https://crontainer.example.com
CRONTAB_PATH=/etc/cron.d
HEALTH_DISK_PATH=/app/data
HEALTH_DISK_MAX_USED_PERCENT=80
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
```

## API

The API uses cookie-based session authentication. Fetch `/api/auth/csrf/` before signing in with `POST /api/auth/login/`, then use `/api/auth/me/` to obtain the current user. The main resources are exposed at:

- `/api/health/` (public system health)
- `/api/dashboard/summary/` (aggregate dashboard counts)
- `/api/schedules/`
- `/api/jobs/` (read-only)
- `/api/credentials/`
- `/api/users/`
- `/api/nodes/`

All non-API routes fall back to the Vue application so browser navigation and refreshes work with its client-side router.

FROM node:22-alpine AS frontend-build

WORKDIR /frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM ghcr.io/astral-sh/uv:0.11.26 AS uv
FROM ubuntu:24.04

# Install system dependencies and required packages
#
RUN apt-get update && apt-get -y install cron python3
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Copy and prepare django application
#
COPY . /app
COPY --from=frontend-build /frontend/dist /app/frontend/dist
RUN mkdir -p /app/data /app/staticfiles \
    && uv run --no-sync python manage.py collectstatic --noinput

CMD ["bin/default_docker_entrypoint.sh"]

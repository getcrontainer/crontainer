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
RUN mkdir /app/data

EXPOSE 8000
CMD ["bin/default_docker_entrypoint.sh"]

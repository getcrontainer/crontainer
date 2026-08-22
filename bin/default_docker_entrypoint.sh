#!/bin/bash

uv run --no-sync python manage.py migrate
uv run --no-sync python manage.py loaddata ./apps/core/fixtures/schedules.yaml
uv run --no-sync python manage.py setup

uv run --no-sync python manage.py update_history &

cron && uv run --no-sync gunicorn crontainer.wsgi -w 2 --bind 0.0.0.0:8000 --workers=4 --threads 3

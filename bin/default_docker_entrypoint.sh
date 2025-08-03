#!/bin/bash

python3 manage.py migrate
python3 manage.py loaddata ./apps/core/fixtures/schedules.yaml
python3 manage.py setup

python3 manage.py update_history &

cron && gunicorn crontainer.wsgi -w 2 --bind 0.0.0.0:8000 --workers=4 --threads 3

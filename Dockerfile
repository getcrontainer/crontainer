FROM python:3.12-slim-bookworm

# Install system dependencies and required packages
#
RUN apt-get update && apt-get -y install cron
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

# Copy and prepare django application
#
COPY . /app
RUN python manage.py migrate
RUN python manage.py loaddata ./apps/core/fixtures/schedules.yaml
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "crontainer.wsgi", "--bind", "0.0.0.0:8000"]

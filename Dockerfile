FROM ubuntu:24.04

# Install system dependencies and required packages
#
RUN apt-get update && apt-get -y install cron python3 python3-pip
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --break-system-packages -r requirements.txt

# Copy and prepare django application
#
COPY . /app
RUN python3 manage.py migrate
RUN python3 manage.py loaddata ./apps/core/fixtures/schedules.yaml
RUN python3 manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "crontainer.wsgi", "--bind", "0.0.0.0:8000"]

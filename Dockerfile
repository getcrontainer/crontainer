FROM python:3.12-slim-bookworm

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

EXPOSE 8000

RUN python manage.py migrate

RUN python manage.py loaddata ./apps/core/fixtures/schedules.yaml

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "crontainer.wsgi", "--bind", "0.0.0.0:8000"]

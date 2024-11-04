FROM python:3.12-slim-bookworm

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 8000

RUN python manage.py migrate

RUN python manage.py loaddata ./apps/core/fixtures/schedules.yaml

CMD ["gunicorn", "crontainer.wsgi", "--bind", "0.0.0.0:8000"]

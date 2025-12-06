FROM python:3.11-slim

WORKDIR /app

COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV DJANGO_SETTINGS_MODULE=backend.settings

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

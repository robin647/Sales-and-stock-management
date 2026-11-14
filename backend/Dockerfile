FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade "pip>=26.2.2" && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN SECRET_KEY="static-build-only-not-runtime-key-0123456789abcdef" \
    ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["python", "start.py"]

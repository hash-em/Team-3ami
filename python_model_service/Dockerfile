# Use a small official Python image
FROM python:3.10-slim

# Keep Python output buffered (helpful for container logging)
ENV PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install system dependencies required for some ML packages (removed after pip install)
# Note: keep packages minimal; add more if your model requires additional native deps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
# The build context for this Dockerfile is expected to be the python_model_service folder,
# so it should contain requirements.txt.
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Copy the service code
COPY . /app

# Make a writable directory for persisted feedback if not present
RUN mkdir -p /app && touch /app/feedback.csv && chmod a+w /app/feedback.csv

# Create an entrypoint script that runs the dev server when FLASK_ENV=development,
# otherwise runs gunicorn for production-like usage.
RUN printf '%s\n' '#!/bin/sh' \
  'set -e' \
  'if [ "$FLASK_ENV" = "development" ] || [ "$DEV" = "1" ]; then' \
  '  echo "Starting Flask dev server (FLASK_ENV=development)";' \
  '  exec python app.py' \
  'else' \
  '  echo "Starting gunicorn: binding to 0.0.0.0:5000";' \
  '  exec gunicorn --workers ${GUNICORN_WORKERS:-2} --bind 0.0.0.0:5000 app:app' \
  'fi' > /entrypoint.sh \
  && chmod +x /entrypoint.sh

EXPOSE 5000

# Healthcheck (optional)
HEALTHCHECK --interval=20s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:5000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD []
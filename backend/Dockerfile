FROM python:3.11-slim

# Allow build-time proxy args to be passed via docker-compose build args
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Export proxy vars into the image environment so apt/pip use them during build
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

WORKDIR /app

# Install system dependencies for GIS/Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
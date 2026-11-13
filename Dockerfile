# ======================================================================
# Production Dockerfile for USeP OBE Syllabus & Class Record Generator
# ======================================================================
FROM python:3.11-slim

# Prevent Python from writing bytecode files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    DATA_DIR=/app/data

WORKDIR /app

# Install lightweight system dependencies (system fonts and curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest and install production packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn>=21.2.0

# Copy application files
COPY . .

# Ensure storage directories exist
RUN mkdir -p /app/data /app/static/signatures /app/exports

# Expose port
EXPOSE 5000

# Health check to ensure Flask application is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/auth/login || exit 1

# Launch production WSGI server
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]

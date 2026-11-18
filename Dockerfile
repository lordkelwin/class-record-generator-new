# ======================================================================
# Cloud Run / Firebase Backend Dockerfile for USeP OBE Studio Pilot
# ======================================================================
FROM python:3.11-slim

# Prevent Python from writing bytecode files, enable unbuffered logs, set Cloud Run port
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/app/data \
    USE_FIREBASE=true \
    FLASK_ENV=production

WORKDIR /app

# Install system fonts, Tesseract OCR engine for built-in Syllabus OCR, and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    fonts-dejavu-core \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies cleanly from requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source, templates, bundled controlled-form fonts (Cinzel-Bold.otf), and curriculum bundles
COPY . .

# Ensure writable runtime directories exist
RUN mkdir -p /app/data /app/static/signatures /app/exports

# Expose Cloud Run / local HTTP port
EXPOSE 8080

# Lightweight health check verifying Flask + Gunicorn readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/api/health || exit 1

# Launch production multi-threaded Gunicorn WSGI server
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]

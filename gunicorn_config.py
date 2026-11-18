"""
Production Gunicorn Configuration for USeP OBE Syllabus & Class Record Generator.
Optimized for Cloud Run & LAN concurrency with long timeouts for PDF/Excel generation.
"""
import multiprocessing
import os

# Network Binding: Cloud Run injects PORT=8080; local containers default to 5000/8080
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Concurrency: gthread worker ensures threads are utilized without multi-process RAM bloat on Cloud Run
_is_cloud_run = bool(os.environ.get("K_SERVICE"))
_default_workers = 1 if _is_cloud_run else min(multiprocessing.cpu_count() * 2 + 1, 2)
workers = int(os.environ.get("WEB_CONCURRENCY", _default_workers))
threads = int(os.environ.get("GUNICORN_THREADS", 8))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

# Timeouts: 120s timeout allows intensive PDF report synthesis, TOS matrices, and Excel exports
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5

# Memory management
max_requests = 1000
max_requests_jitter = 50

# Logging: stream access & error logs to stdout/stderr for Cloud Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

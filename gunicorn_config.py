"""
Production Gunicorn Configuration for USeP OBE Syllabus & Class Record Generator.
Optimized for concurrent web traffic and long-running PDF/Excel compilation tasks.
"""
import multiprocessing
import os

# Network Binding: bind to PORT specified by cloud environment (Render, Railway, Heroku, etc.)
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Concurrency: balance CPU cores with available RAM
_default_workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
workers = int(os.environ.get("WEB_CONCURRENCY", _default_workers))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "sync"

# Timeouts: 120s timeout allows intensive PDF report synthesis, complex TOS matrices,
# and Excel export operations to complete without premature 504 Gateway Timeouts.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5

# Memory management: restart workers after serving requests to prevent memory bloat
max_requests = 1000
max_requests_jitter = 50

# Logging: pipe logs to standard stdout/stderr for Docker, PaaS, and journalctl
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

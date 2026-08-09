"""Prometheus metrics endpoint and basic instrumentation.

Exposes a /metrics endpoint for scraping (UptimeRobot-style or Grafana).
Uses prometheus-client when available; falls back to a plain JSON payload
so the app still boots without it.
"""

import time
from functools import wraps

from app.core.config import settings

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

    class _NoopCollector:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    Counter = _NoopCollector
    Histogram = _NoopCollector


if HAS_PROMETHEUS:
    REQUEST_COUNT = Counter(
        "retailiq_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "retailiq_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )
else:
    REQUEST_COUNT = _NoopCollector()
    REQUEST_LATENCY = _NoopCollector()


def instrument_request(method: str, path: str):
    """Decorator: time a handler and record the outcome."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                status = getattr(result, "status_code", 200)
                REQUEST_COUNT.labels(method, path, str(status)).inc()
                return result
            except Exception:
                REQUEST_COUNT.labels(method, path, "500").inc()
                raise
            finally:
                REQUEST_LATENCY.labels(method, path).observe(time.perf_counter() - start)
        return wrapper
    return decorator


def metrics_response():
    """Return the metrics payload appropriate for the installed prometheus-client."""
    if HAS_PROMETHEUS:
        return generate_latest(), CONTENT_TYPE_LATEST
    return (
        "retailiq_metrics_enabled 0\n",
        "text/plain; version=0.0.4; charset=utf-8",
    )


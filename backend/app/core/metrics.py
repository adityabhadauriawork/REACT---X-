"""
SIH26162 — Prometheus Operational Metrics Registry
Provides lightweight, read-only operational telemetry for API latency, FIRMS ingestion,
ML inference performance, and industrial telemetry connection health.
"""
import time
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# =========================================================================
# PROMETHEUS METRIC DEFINITIONS
# =========================================================================

if PROMETHEUS_AVAILABLE:
    # 1. HTTP Traffic & Latency
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total count of HTTP requests processed by REACT-X API",
        ["method", "path_group", "status_code"]
    )
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency histogram in seconds",
        ["method", "path_group"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )

    # 2. NASA FIRMS Satellite Ingestion
    FIRMS_INGESTION_CYCLES_TOTAL = Counter(
        "firms_ingestion_cycles_total",
        "Total NASA FIRMS background polling cycles executed",
        ["status"]
    )
    FIRMS_EVENTS_FETCHED_TOTAL = Counter(
        "firms_events_fetched_total",
        "Total raw thermal events received from NASA FIRMS"
    )
    FIRMS_EVENTS_PERSISTED_TOTAL = Counter(
        "firms_events_persisted_total",
        "Total canonical thermal events persisted into REACT-X database"
    )
    FIRMS_INGESTION_FAILURES_TOTAL = Counter(
        "firms_ingestion_failures_total",
        "Total failed NASA FIRMS polling / ingestion cycles"
    )

    # 3. Machine Learning Inference
    ML_INFERENCE_TOTAL = Counter(
        "ml_inference_total",
        "Total ML classifier predictions executed",
        ["model", "predicted_class"]
    )
    ML_INFERENCE_DURATION_SECONDS = Histogram(
        "ml_inference_duration_seconds",
        "ML classifier inference latency in seconds",
        ["model"],
        buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
    )

    # 4. Industrial Telemetry Protocol Connections
    TELEMETRY_ACTIVE_CONNECTIONS = Gauge(
        "telemetry_active_connections",
        "Number of active industrial protocol connections (OPC UA, MQTT, Modbus)",
        ["protocol"]
    )

    # 5. Database & Worker Health
    DATABASE_HEALTH_STATUS = Gauge(
        "database_health_status",
        "Database connectivity status (1 = Healthy, 0 = Degraded/Unavailable)"
    )
    DATABASE_HEALTH_STATUS.set(1)

    FIRMS_LAST_INGESTION_TIMESTAMP = Gauge(
        "firms_last_ingestion_timestamp_seconds",
        "Unix timestamp of the most recent successful NASA FIRMS ingestion cycle"
    )
    FIRMS_LAST_INGESTION_TIMESTAMP.set(time.time())

    # 6. System Metadata
    SYSTEM_BUILD_INFO = Gauge(
        "system_build_info",
        "System build version and metadata",
        ["version", "service"]
    )
    SYSTEM_BUILD_INFO.labels(version="2.0.0", service="REACT-X").set(1)

else:
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION_SECONDS = None
    FIRMS_INGESTION_CYCLES_TOTAL = None
    FIRMS_EVENTS_FETCHED_TOTAL = None
    FIRMS_EVENTS_PERSISTED_TOTAL = None
    FIRMS_INGESTION_FAILURES_TOTAL = None
    ML_INFERENCE_TOTAL = None
    ML_INFERENCE_DURATION_SECONDS = None
    TELEMETRY_ACTIVE_CONNECTIONS = None
    DATABASE_HEALTH_STATUS = None
    FIRMS_LAST_INGESTION_TIMESTAMP = None
    SYSTEM_BUILD_INFO = None



# =========================================================================
# HELPER FUNCTIONS FOR APPLICATION CODE
# =========================================================================

def record_http_metrics(method: str, path_group: str, status_code: int, duration_sec: float):
    """Records HTTP request count and duration histogram."""
    if PROMETHEUS_AVAILABLE:
        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path_group=path_group,
                status_code=str(status_code)
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                path_group=path_group
            ).observe(duration_sec)
        except Exception:
            pass


def record_firms_cycle(status: str = "success"):
    """Records completion of a NASA FIRMS polling cycle."""
    if PROMETHEUS_AVAILABLE:
        try:
            FIRMS_INGESTION_CYCLES_TOTAL.labels(status=status).inc()
            if status != "success":
                FIRMS_INGESTION_FAILURES_TOTAL.inc()
        except Exception:
            pass


def record_firms_events(fetched: int = 0, persisted: int = 0):
    """Records counts of fetched and persisted thermal events."""
    if PROMETHEUS_AVAILABLE:
        try:
            if fetched > 0:
                FIRMS_EVENTS_FETCHED_TOTAL.inc(fetched)
            if persisted > 0:
                FIRMS_EVENTS_PERSISTED_TOTAL.inc(persisted)
        except Exception:
            pass


def record_ml_inference(model: str, predicted_class: str, duration_sec: float):
    """Records ML classifier prediction and inference duration."""
    if PROMETHEUS_AVAILABLE:
        try:
            ML_INFERENCE_TOTAL.labels(
                model=model,
                predicted_class=predicted_class
            ).inc()
            ML_INFERENCE_DURATION_SECONDS.labels(
                model=model
            ).observe(duration_sec)
        except Exception:
            pass


def set_telemetry_connections(protocol: str, count: int):
    """Updates active telemetry protocol connection count."""
    if PROMETHEUS_AVAILABLE:
        try:
            TELEMETRY_ACTIVE_CONNECTIONS.labels(protocol=protocol).set(count)
        except Exception:
            pass


def get_prometheus_metrics_bytes() -> bytes:
    """Renders all registered Prometheus metrics to standard Prometheus text format."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY)
    return b"# prometheus_client not installed\n"


# =========================================================================
# FASTAPI PROMETHEUS HTTP MIDDLEWARE
# =========================================================================

def _normalize_path(path: str) -> str:
    """Normalizes API path to low-cardinality group to avoid label explosion."""
    if path.startswith("/api/thermal/events"):
        return "/api/thermal/events"
    elif path.startswith("/api/thermal/sources"):
        return "/api/thermal/sources"
    elif path.startswith("/api/facilities"):
        return "/api/facilities"
    elif path.startswith("/api/scenarios"):
        return "/api/scenarios"
    elif path.startswith("/api/hazard"):
        return "/api/hazard"
    elif path.startswith("/api/impact"):
        return "/api/impact"
    elif path.startswith("/api/evacuation"):
        return "/api/evacuation"
    elif path.startswith("/api/satellite"):
        return "/api/satellite"
    elif path.startswith("/api/"):
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return f"/{parts[0]}/{parts[1]}"
        return path
    elif path == "/metrics" or path == "/health" or path == "/readiness":
        return path
    return "/"


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Measures latency and records request counts per normalized path group and status code.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start_time
            path_group = _normalize_path(request.url.path)
            record_http_metrics(
                method=request.method,
                path_group=path_group,
                status_code=status_code,
                duration_sec=duration
            )

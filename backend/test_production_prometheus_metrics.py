"""
Integration and format tests for Prometheus /metrics operational exporter.
Validates:
- GET /metrics returns HTTP 200 with standard Prometheus content type
- Presence of http_requests_total, firms_ingestion_cycles_total, ml_inference_total, system_build_info
- Recording of HTTP latency and request count
- Recording of ML inference latency and classification counts
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.metrics import (
    record_firms_cycle,
    record_firms_events,
    record_ml_inference,
    set_telemetry_connections
)

client = TestClient(app)


def test_prometheus_metrics_endpoint():
    """Verify /metrics returns HTTP 200 with text/plain format and standard metric families."""
    # Issue a dummy request to populate HTTP metrics
    client.get("/api/version")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")

    content = response.text
    assert "system_build_info" in content
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content
    assert "firms_ingestion_cycles_total" in content
    assert "ml_inference_total" in content


def test_prometheus_manual_metric_recordings():
    """Verify manual helper recordings appear in the /metrics output."""
    record_firms_cycle("success")
    record_firms_events(fetched=15, persisted=12)
    record_ml_inference(model="HistGradientBoostingClassifier", predicted_class="INDUSTRIAL_FLARE", duration_sec=0.0012)
    set_telemetry_connections(protocol="OPC_UA", count=4)

    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text

    assert 'predicted_class="INDUSTRIAL_FLARE"' in content
    assert 'telemetry_active_connections{protocol="OPC_UA"} 4.0' in content
    assert "firms_events_fetched_total" in content
    assert "firms_events_persisted_total" in content

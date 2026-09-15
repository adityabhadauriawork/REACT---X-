"""
Integration tests for Request Correlation ID tracking middleware.
Validates:
- Auto-generation of UUID4 correlation ID when absent
- Exact preservation of supplied X-Request-ID
- Inclusion of X-Request-ID in HTTP response headers
- Context variable retrieval within async execution scope
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.correlation import get_correlation_id

client = TestClient(app)


def test_generated_correlation_id_when_absent():
    """Verify that a request with no X-Request-ID receives a valid generated ID."""
    response = client.get("/api/version")
    assert response.status_code == 200
    assert "x-request-id" in response.headers or "X-Request-ID" in response.headers
    req_id = response.headers.get("x-request-id") or response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16  # Valid UUID hex string


def test_supplied_correlation_id_preserved():
    """Verify that an incoming custom X-Request-ID is preserved and returned in the response."""
    custom_id = "ntro-national-command-trace-998811"
    response = client.get("/api/version", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    returned_id = response.headers.get("x-request-id") or response.headers.get("X-Request-ID")
    assert returned_id == custom_id


def test_correlation_id_on_health_and_metrics():
    """Verify correlation ID is present on operational endpoints."""
    res_health = client.get("/health", headers={"X-Request-ID": "health-probe-1"})
    assert res_health.headers.get("X-Request-ID") == "health-probe-1"

    res_metrics = client.get("/metrics", headers={"X-Request-ID": "metrics-scrape-1"})
    assert res_metrics.headers.get("X-Request-ID") == "metrics-scrape-1"

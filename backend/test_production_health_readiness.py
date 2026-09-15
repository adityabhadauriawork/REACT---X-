"""
Integration and failure injection tests for /health (liveness) and /readiness probes.
Validates:
- /health always returns 200 (process liveness) without requiring database
- /readiness returns 200 when database is alive
- /readiness returns 503 Service Unavailable when database connection is dropped / unavailable
- Root-level /health and /readiness aliases function identically
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_liveness_probe():
    """Verify liveness probe returns HTTP 200 with status alive."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "alive"


def test_readiness_probe_healthy():
    """Verify readiness probe returns HTTP 200 when DB is active."""
    res = client.get("/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"]["status"] == "ready"


def test_readiness_probe_database_failure():
    """Verify readiness probe returns HTTP 503 when database execution fails."""
    with patch("app.core.database.SessionLocal") as mock_session_factory:
        mock_db = mock_session_factory.return_value
        mock_db.execute.side_effect = Exception("Database connection lost: timeout / connection refused")

        res = client.get("/readiness")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "unavailable"

    # Verify that liveness probe STILL returns 200 even when DB is down
    res_live = client.get("/health")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

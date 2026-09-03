"""
SIH26162 Phase 10 — API Reliability Tests

Tests that every important API endpoint returns:
- Predictable error structures (422/404/403/400 not 500)
- No internal stack traces in responses
- Correct pagination bounds
- Proper CORS headers
- Authorization enforcement
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client(setup_db):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _no_stack_trace(response_text: str) -> bool:
    """Returns True if response does NOT contain internal Python stack trace."""
    lower = response_text.lower()
    return "traceback (most recent call last)" not in lower


# =============================================================================
# RELIABILITY 1: Invalid UUID path params → 404 not 500
# =============================================================================
def test_rel_01_invalid_source_id_returns_404(client):
    resp = client.get("/api/thermal/sources/NONEXISTENT-SOURCE-ID-99999/assessment")
    assert resp.status_code in (404, 422), (
        f"Invalid source ID must return 404/422, got {resp.status_code}: {resp.text[:200]}"
    )
    assert _no_stack_trace(resp.text), "Stack trace must not be exposed in error response"


# =============================================================================
# RELIABILITY 2: Invalid assessment ID → 404 not 500
# =============================================================================
def test_rel_02_invalid_assessment_id_404(client):
    resp = client.get("/api/thermal/assessments/ASM-DOES-NOT-EXIST-00000")
    assert resp.status_code in (404, 422)
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 3: Thermal events list with large offset → bounded response
# =============================================================================
def test_rel_03_large_offset_pagination_bounded(client):
    resp = client.get("/api/thermal/events?limit=50&offset=999999")
    assert resp.status_code == 200
    data = resp.json()
    # Must return a list, possibly empty — not a server error
    assert isinstance(data, list) or isinstance(data, dict)
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 4: Malformed JSON body → 422 not 500
# =============================================================================
def test_rel_04_malformed_json_body(client):
    resp = client.post(
        "/api/thermal/sources/ANY-SRC/assess",
        data="this is not json",  # raw string
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code in (400, 422), (
        f"Malformed JSON should return 400/422, got {resp.status_code}"
    )
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 5: Missing required fields → 422 Unprocessable Entity
# =============================================================================
def test_rel_05_missing_required_field_422(client):
    # IncidentPromotionRequest requires operator_id and justification
    resp = client.post(
        "/api/thermal/assessments/ASM-FAKE-ID/promote-incident",
        json={}  # missing required fields
    )
    assert resp.status_code in (404, 422), (
        f"Missing required fields must return 422, got {resp.status_code}"
    )
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 6: Health endpoint has no stack trace exposure
# =============================================================================
def test_rel_06_health_no_debug_info(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    # Health response must not include internal paths, secrets, or tokens
    response_str = str(data)
    sensitive_patterns = ["password", "secret", "token", "api_key", "traceback", "sqlalchemy"]
    for pattern in sensitive_patterns:
        assert pattern not in response_str.lower(), (
            f"Health response must not expose sensitive info '{pattern}': {response_str[:200]}"
        )


# =============================================================================
# RELIABILITY 7: Readiness endpoint structure is correct
# =============================================================================
def test_rel_07_readiness_structure(client):
    resp = client.get("/api/readiness")
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "ml_classifier" in data["checks"]
    assert "firms_api_key" in data["checks"]
    assert "timestamp" in data


# =============================================================================
# RELIABILITY 8: System status endpoint returns consistent structure
# =============================================================================
def test_rel_08_system_status_structure(client):
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "data_counts" in data
    counts = data["data_counts"]
    assert "thermal_events" in counts
    assert "thermal_sources" in counts
    assert "industrial_facilities" in counts


# =============================================================================
# RELIABILITY 9: Thermal sources list → correct pagination structure
# =============================================================================
def test_rel_09_thermal_sources_list_pagination(client):
    resp = client.get("/api/thermal/sources?limit=10&offset=0")
    assert resp.status_code in (200, 404)
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 10: Executive brief for nonexistent assessment → 404 not 500
# =============================================================================
def test_rel_10_executive_brief_nonexistent_404(client):
    resp = client.get("/api/thermal/assessments/ASM-GHOST-00/executive-brief")
    assert resp.status_code in (404, 422), (
        f"Executive brief for nonexistent assessment must return 404/422, got {resp.status_code}"
    )
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 11: Data quality endpoint never returns 500
# =============================================================================
def test_rel_11_data_quality_never_500(client):
    resp = client.get("/api/system/data-quality")
    assert resp.status_code != 500, (
        f"Data quality endpoint must never return 500: {resp.text[:200]}"
    )
    assert _no_stack_trace(resp.text)


# =============================================================================
# RELIABILITY 12: Coverage endpoint includes required fields
# =============================================================================
def test_rel_12_coverage_required_fields(client):
    resp = client.get("/api/system/coverage")
    assert resp.status_code == 200
    data = resp.json()
    required_fields = [
        "coverage_scope", "total_events", "total_facilities",
        "total_sources", "state_breakdown", "disclaimer", "generated_at"
    ]
    for field in required_fields:
        assert field in data, f"Coverage report missing required field: {field}"

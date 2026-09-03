import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.services.site.site_service import site_service
from app.services.satellite.firms_service import firms_service
from app.services.satellite.firms_ingestion_service import firms_ingestion_service

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    site_service.load_seed_data_if_empty(db)
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

MOCK_VIIRS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
21.6852,72.5753,348.2,0.38,0.37,2026-08-30,0845,N,h,1.0NRT,298.4,84.6,N
22.3880,69.8320,365.4,0.40,0.38,2026-08-30,0915,NPP,h,1.0NRT,305.1,320.0,N
21.1210,72.6450,338.0,0.37,0.36,2026-08-30,0930,21,n,1.0NRT,295.0,28.4,D
"""

MOCK_MODIS_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight
22.3950,82.7210,329.5,1.1,1.0,2026-08-30,1030,T,85,6.1NRT,290.0,48.0,D
22.8020,86.2030,334.2,1.0,1.0,2026-08-30,1145,A,88,6.1NRT,292.5,39.5,D
"""

def test_firms_url_builder():
    """Verify URL construction across VIIRS and MODIS constellations."""
    url_viirs = firms_ingestion_service.build_firms_url("VIIRS_NOAA20_NRT", bbox="68.0,20.0,75.0,25.0", days=1)
    assert "VIIRS_NOAA20_NRT" in url_viirs
    assert "68.0,20.0,75.0,25.0" in url_viirs
    assert url_viirs.endswith("/1")

def test_firms_csv_parsing():
    """Verify parsing of VIIRS and MODIS CSV responses into structured records."""
    viirs_records = firms_ingestion_service.parse_firms_csv(MOCK_VIIRS_CSV, "VIIRS_NOAA20_NRT")
    assert len(viirs_records) == 3
    assert float(viirs_records[0]["latitude"]) == 21.6852
    assert float(viirs_records[0]["frp"]) == 84.6
    assert viirs_records[0]["confidence"] == "h"

    modis_records = firms_ingestion_service.parse_firms_csv(MOCK_MODIS_CSV, "MODIS_NRT")
    assert len(modis_records) == 2
    assert float(modis_records[0]["brightness"]) == 329.5
    assert modis_records[0]["confidence"] == "85"

def test_firms_empty_and_error_handling():
    """Verify parsing handles empty bodies, no data, and invalid map keys."""
    assert firms_ingestion_service.parse_firms_csv("", "VIIRS_NOAA20_NRT") == []
    assert firms_ingestion_service.parse_firms_csv("No data", "VIIRS_NOAA20_NRT") == []

    with pytest.raises(ValueError, match="Invalid MAP_KEY"):
        firms_ingestion_service.parse_firms_csv("Invalid MAP_KEY", "VIIRS_NOAA20_NRT")

@pytest.mark.anyio
async def test_firms_fetch_with_mocked_success():
    """Verify resilient HTTP fetching when NASA API returns valid CSV."""
    with patch.object(settings, "NASA_FIRMS_MAP_KEY", "TEST_KEY_1234567890"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_VIIRS_CSV

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch.object(firms_ingestion_service, "_get_client", return_value=mock_client):
            records = await firms_ingestion_service.fetch_source_records("VIIRS_NOAA20_NRT")
            assert len(records) == 3

@pytest.mark.anyio
async def test_firms_rate_limiting_and_retry():
    """Verify exponential backoff when NASA API returns HTTP 429 Rate Limit."""
    with patch.object(settings, "NASA_FIRMS_MAP_KEY", "TEST_KEY_1234567890"):
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0.01"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = MOCK_VIIRS_CSV

        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_response_429, mock_response_200]

        with patch.object(firms_ingestion_service, "_get_client", return_value=mock_client):
            records = await firms_ingestion_service.fetch_source_records("VIIRS_NOAA20_NRT")
            assert len(records) == 3
            assert mock_client.get.call_count == 2

@pytest.mark.anyio
async def test_firms_end_to_end_ingestion_cycle():
    """Verify full end-to-end ingestion cycle from HTTP mock to database persistence."""
    with patch.object(settings, "NASA_FIRMS_MAP_KEY", "TEST_KEY_1234567890"):
        with patch.object(firms_ingestion_service, "fetch_source_records", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [
                firms_ingestion_service.parse_firms_csv(MOCK_VIIRS_CSV, "VIIRS_NOAA20_NRT"),
                firms_ingestion_service.parse_firms_csv(MOCK_MODIS_CSV, "MODIS_NRT"),
                [],
                []
            ]

            db = TestingSessionLocal()
            summary = await firms_ingestion_service.run_ingestion_cycle(db=db)
            db.close()

            assert summary.records_received == 5
            assert summary.records_persisted >= 3
            assert summary.duplicates_skipped >= 0

def test_feed_status_api_endpoint():
    """Verify GET /api/thermal/feed/status returns complete observability diagnostics."""
    res = client.get("/api/thermal/feed/status")
    assert res.status_code == 200
    status_data = res.json()
    assert "api_health_status" in status_data
    assert "poll_interval_minutes" in status_data
    assert "configured_sources" in status_data
    assert "records_received_total" in status_data

@pytest.mark.anyio
async def test_manual_poll_api_endpoint():
    """Verify POST /api/thermal/feed/poll executes manual on-demand poll."""
    with patch.object(firms_ingestion_service, "run_ingestion_cycle", new_callable=AsyncMock) as mock_cycle:
        from app.schemas.thermal import FIRMSIngestSummaryResponse
        mock_cycle.return_value = FIRMSIngestSummaryResponse(
            source="NASA_FIRMS",
            records_received=3,
            records_parsed=3,
            records_validated=3,
            duplicates_skipped=0,
            records_persisted=3,
            records_flagged_warning=0,
            records_rejected_invalid=0,
            ingestion_duration_ms=45.2,
            inserted_event_ids=["FIRMS-NOAA20-TEST-01"],
            quality_summary={"GOOD": 3}
        )

        res = client.post("/api/thermal/feed/poll?days=1")
        assert res.status_code == 200
        data = res.json()
        assert data["records_received"] == 3
        assert data["records_persisted"] == 3

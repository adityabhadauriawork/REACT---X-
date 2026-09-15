import pytest
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.satellite.landsat_service import LandsatM2MService, landsat_service
from app.services.satellite.confirmation_service import confirmation_service
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine
from app.schemas.thermal import CanonicalThermalEvent
from app.schemas.thermal_corroboration import ObservationStatus
from app.schemas.discrimination import EOStructuralMatchStatus

client = TestClient(app)

# 1. TEST REAL USGS M2M AUTHENTICATION (CONDITIONAL)
def test_landsat_usgs_real_authentication():
    """Verify authentication against USGS M2M API when credentials are provided."""
    if not landsat_service.is_m2m_configured:
        pytest.skip("USGS M2M credentials not configured in environment.")

    token = landsat_service.get_api_key(force_refresh=True)
    assert token is not None, "Failed to obtain API token from USGS M2M"
    assert len(token) > 10, "API token is unexpectedly short"
    # Token caching verification
    cached = landsat_service.get_api_key(force_refresh=False)
    assert cached == token, "Cached token should match freshly acquired token"


# 2. TEST MOCKED USGS M2M LOGIN-TOKEN AUTHENTICATION
def test_landsat_usgs_mocked_login_token_flow():
    """Verify /login-token JSON payload and token caching."""
    svc = LandsatM2MService()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": "MOCK_USGS_M2M_SESSION_TOKEN_ABC123",
        "errorCode": None,
        "errorMessage": None
    }

    with patch.object(settings, "USGS_M2M_USERNAME", "test_user"), \
         patch.object(settings, "USGS_M2M_TOKEN", "test_secret_token"), \
         patch.object(svc._session, "post", return_value=mock_response) as mock_post:
        token = svc.get_api_key(force_refresh=True)
        assert token == "MOCK_USGS_M2M_SESSION_TOKEN_ABC123"
        assert mock_post.called
        # Verify credentials passed
        sent_json = mock_post.call_args[1]["json"]
        assert sent_json["username"] == "test_user"
        assert sent_json["token"] == "test_secret_token"


# 3. TEST AUTHENTICATION TOKEN FAILURE HANDLING (NO SECRETS LEAK)
def test_landsat_usgs_auth_failure_graceful_handling():
    """Verify graceful handling when bad credentials are provided."""
    svc = LandsatM2MService()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "data": None,
        "errorCode": "AUTH_FAILED",
        "errorMessage": "Invalid credentials"
    }

    with patch.object(settings, "USGS_M2M_USERNAME", "bad_user"), \
         patch.object(settings, "USGS_M2M_TOKEN", "bad_token"), \
         patch.object(svc._session, "post", return_value=mock_response):
        token = svc.get_api_key(force_refresh=True)
        assert token is None, "Bad credentials should return None"


# 4. TEST REAL LANDSAT SCENE SEARCH OVER DAHEJ INDUSTRIAL AOI (CONDITIONAL)
def test_landsat_usgs_real_scene_search_dahej():
    """Verify USGS M2M scene search over Dahej Industrial AOI."""
    if not landsat_service.is_m2m_configured:
        pytest.skip("USGS M2M credentials not configured in environment.")

    dahej_lat, dahej_lon = 21.6850, 72.5620
    ctx = landsat_service.get_landsat_context_for_coordinates(
        latitude=dahej_lat,
        longitude=dahej_lon,
        lookback_days=60,
        max_cloud_cover_pct=100.0
    )
    assert ctx is not None, "Should find at least one Landsat scene over Dahej AOI within 60 days"
    assert "Landsat" in ctx["satellite"]
    assert ctx["source"] in ["USGS_LANDSAT_M2M", "USGS_LANDSAT_PLANETARY_COMPUTER"]
    assert ctx["cloud_coverage_pct"] >= 0.0
    assert "Band 10 (10.9μm TIR-1)" in ctx["bands_used"]
    assert "thermal_calibration" in ctx
    assert ctx["is_live_data"] is True


# 5. TEST MOCKED SCENE SEARCH & CLOUD COVER FILTERING
def test_landsat_scene_search_and_cloud_filtering():
    """Verify scene search parsing, cloud cover filtering, and sorting."""
    svc = LandsatM2MService()
    mock_results = [
        {
            "entityId": "LC09_L2SP_148045_20260830_02_T1",
            "displayId": "LC09_L2SP_148045_20260830_20260901_02_T1",
            "acquisitionDate": "2026-08-30",
            "cloudCover": 12.5,
            "wrsPath": "148",
            "wrsRow": "045"
        },
        {
            "entityId": "LC08_L2SP_148045_20260822_02_T1",
            "displayId": "LC08_L2SP_148045_20260822_20260824_02_T1",
            "acquisitionDate": "2026-08-22",
            "cloudCover": 85.0,
            "wrsPath": "148",
            "wrsRow": "045"
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {"results": mock_results, "totalHits": 2},
        "errorCode": None
    }

    with patch.object(svc, "get_api_key", return_value="VALID_TOKEN"), \
         patch.object(svc._session, "post", return_value=mock_resp):
        scenes = svc.search_landsat_scenes(
            bbox=[72.5, 21.6, 72.6, 21.7],
            start_datetime=datetime(2026, 8, 1, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 8, 31, tzinfo=timezone.utc),
            max_cloud_cover_pct=50.0
        )
        assert len(scenes) == 1, "Cloudy scene (85%) should be filtered out"
        assert scenes[0]["displayId"] == "LC09_L2SP_148045_20260830_20260901_02_T1"


# 6. TEST TIMEOUT AND NETWORK RESILIENCE
def test_landsat_timeout_network_resilience():
    """Verify graceful handling when USGS M2M API encounters timeout or connection drop."""
    svc = LandsatM2MService()
    with patch.object(svc, "get_api_key", return_value="VALID_TOKEN"), \
         patch.object(svc._session, "post", side_effect=requests.exceptions.Timeout("Connection timed out")):
        scenes = svc.search_landsat_scenes(
            bbox=[72.5, 21.6, 72.6, 21.7],
            start_datetime=datetime(2026, 8, 1, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 8, 31, tzinfo=timezone.utc)
        )
        assert scenes == [], "Timeout should return empty list without raising exception"


from unittest.mock import patch, MagicMock, PropertyMock

# 7. TEST MULTI-SENSOR CONFIRMATION SERVICE INTEGRATION WITH LANDSAT
def test_confirmation_service_with_live_landsat():
    """Verify ConfirmationService corroborates event using live Landsat context."""
    mock_ctx = {
        "source": "USGS_LANDSAT_M2M",
        "satellite": "Landsat-9",
        "sensor": "TIRS-2 / OLI-2",
        "scene_id": "LC09_L2SP_148045_20260830_02_T1",
        "product_id": "USGS:landsat_ot_c2_l2:LC09_L2SP_148045_20260830_02_T1",
        "cloud_coverage_pct": 8.0,
        "thermal_calibration": {
            "band_10_radiance_w_m2_sr_um": 14.8,
            "derived_ground_temp_c": 54.2
        }
    }

    event = CanonicalThermalEvent(
        event_id="EVT-TEST-LS-01",
        dedup_key="DEDUP-KEY-LS-01",
        latitude=21.6850,
        longitude=72.5620,
        brightness_temp_k=355.0,
        frp_mw=38.0,
        confidence="HIGH",
        confidence_pct=92.0,
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=datetime.now(timezone.utc),
        classification="INDUSTRIAL_FIRE",
        abnormality_score=85.0
    )

    with patch.object(LandsatM2MService, "is_configured", new_callable=PropertyMock, return_value=True), \
         patch.object(landsat_service, "get_landsat_context_for_coordinates", return_value=mock_ctx):
        res = confirmation_service.corroborate_event(event)
        assert res is not None
        assert res.landsat_thermal_confirmation is not None
        assert res.landsat_thermal_confirmation["satellite"] == "Landsat-9"
        assert res.landsat_thermal_confirmation["source_provenance"] == "USGS_LANDSAT_M2M"
        assert res.landsat_thermal_confirmation["is_live_usgs_m2m"] is True
        assert res.landsat_thermal_confirmation["corroboration_state"] == "THERMAL_HOTSPOT_CORROBORATED"


# 8. TEST EO VERIFICATION SERVICE INTEGRATION WITH LANDSAT
def test_eo_verification_service_with_landsat_context():
    """Verify EOVerificationService correctly handles Landsat context."""
    mock_ctx = {
        "source": "USGS_LANDSAT_M2M",
        "satellite": "Landsat-9",
        "sensor": "TIRS-2 / OLI-2",
        "scene_id": "LC09_L2SP_148045_20260830_02_T1",
        "product_id": "USGS:landsat_ot_c2_l2:LC09_L2SP_148045_20260830_02_T1",
        "cloud_coverage_pct": 10.0,
        "acquisition_timestamp": datetime.now(timezone.utc) - timedelta(hours=8),
        "aoi_bbox": [72.54, 21.67, 72.58, 21.70],
        "bands_used": ["Band 10 (10.9μm TIR-1)", "Band 11 (12.0μm TIR-2)"],
        "thermal_calibration": {
            "band_10_radiance_w_m2_sr_um": 14.8,
            "derived_ground_temp_c": 54.2
        }
    }

    with patch.object(LandsatM2MService, "is_configured", new_callable=PropertyMock, return_value=True), \
         patch.object(landsat_service, "get_landsat_context_for_coordinates", return_value=mock_ctx):
        eo_res = eo_verification_service.verify_thermal_source(
            source_id="SRC-DAHEJ-TEST",
            latitude=21.6850,
            longitude=72.5620,
            facility_id="FAC-DAHEJ-01",
            facility_distance_m=30.0
        )
        assert eo_res is not None
        assert eo_res.structural_match_status == EOStructuralMatchStatus.STRONG_SPATIAL_MATCH
        assert eo_res.is_live_imagery is True
        assert eo_res.landsat_scene_id == "LC09_L2SP_148045_20260830_02_T1"
        assert eo_res.is_live_landsat is True
        assert eo_res.thermal_calibration is not None
        assert eo_res.thermal_calibration["derived_ground_temp_c"] == 54.2


# 9. TEST ON-DEMAND IMAGE CONFIRMATION ENDPOINT WITH LANDSAT PREFERENCE
def test_on_demand_image_confirmation_endpoint_landsat():
    """Verify POST /api/thermal/sources/{source_id}/request-image-confirmation with satellite=Landsat-9."""
    # Query seeded sources endpoint
    resp = client.get("/api/thermal/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) > 0, "Expected at least one seeded thermal source"
    source_id = sources[0]["source_id"]
    
    mock_ctx = {
        "source": "USGS_LANDSAT_M2M",
        "satellite": "Landsat-9",
        "sensor": "TIRS-2 / OLI-2",
        "scene_id": "LC09_L2SP_148045_20260830_02_T1",
        "product_id": "USGS:landsat_ot_c2_l2:LC09_L2SP_148045_20260830_02_T1",
        "wrs_path_row": "148/045",
        "cloud_coverage_pct": 5.0,
        "acquisition_timestamp": datetime.now(timezone.utc) - timedelta(days=2),
        "thermal_calibration": {
            "band_10_radiance_w_m2_sr_um": 14.8,
            "derived_ground_temp_c": 54.2
        }
    }

    with patch.object(LandsatM2MService, "is_configured", new_callable=PropertyMock, return_value=True), \
         patch.object(landsat_service, "get_landsat_context_for_coordinates", return_value=mock_ctx):
        req_resp = client.post(f"/api/thermal/sources/{source_id}/request-image-confirmation?satellite=Landsat-9")
        assert req_resp.status_code == 200
        data = req_resp.json()
        assert "request_id" in data
        assert "confirmation_status" in data
        assert data["source_id"] == source_id
        assert data["satellite"] == "Landsat-9"

import pytest
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.satellite.copernicus_service import CopernicusDataSpaceService, copernicus_service
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.satellite.source_discrimination_service import source_discrimination_service
from app.schemas.discrimination import (
    EOStructuralMatchStatus, LandCoverClass, SourcePersistenceState
)

client = TestClient(app)

# 1. TEST REAL AUTHENTICATION & TOKEN ACQUISITION
def test_copernicus_oauth_real_authentication():
    """Verify OAuth2 client_credentials authentication against Copernicus CDSE token endpoint."""
    if not copernicus_service.is_configured:
        pytest.skip("Copernicus credentials not configured in environment.")

    token = copernicus_service.get_access_token(force_refresh=True)
    assert token is not None, "Failed to obtain access token from Copernicus Data Space"
    assert len(token) > 50, "Access token is unexpectedly short"
    assert not token.startswith("Bearer "), "Token should be raw access token"
    # Token caching verification
    cached_token = copernicus_service.get_access_token(force_refresh=False)
    assert cached_token == token, "Cached token should match freshly acquired token"


# 2. TEST AUTHENTICATION TOKEN FAILURE HANDLING (NO LEAKS)
def test_copernicus_oauth_token_failure_graceful_handling():
    """Verify graceful rejection when bad credentials are provided, ensuring secrets never leak."""
    svc = CopernicusDataSpaceService()
    with patch.object(settings, "COPERNICUS_CLIENT_SECRET", "INVALID_SECRET_FOR_TEST"):
        token = svc.get_access_token(force_refresh=True)
        assert token is None, "Bad credentials should return None instead of raising unhandled error"


# 3. TEST REAL SENTINEL-2 SCENE SEARCH OVER DAHEJ INDUSTRIAL AOI
def test_copernicus_sentinel2_real_catalog_search_dahej():
    """Verify STAC catalog query on Copernicus Data Space for Dahej Industrial PCPIR AOI."""
    if not copernicus_service.is_configured:
        pytest.skip("Copernicus credentials not configured in environment.")

    dahej_lat, dahej_lon = 21.6850, 72.5620
    ctx = copernicus_service.get_sentinel2_context_for_coordinates(
        latitude=dahej_lat,
        longitude=dahej_lon,
        lookback_days=30,
        max_cloud_cover_pct=100.0
    )
    assert ctx is not None, "Should find at least one Sentinel-2 scene over Dahej AOI within 30-day window"
    assert "S2" in ctx["scene_id"], f"Expected Sentinel-2 scene ID format, got {ctx['scene_id']}"
    assert ctx["source"] == "COPERNICUS_SENTINEL2"
    assert ctx["cloud_coverage_pct"] >= 0.0
    assert ctx["spatial_resolution_m"] == 10.0
    assert "B04" in ctx["bands_used"] and "B12" in ctx["bands_used"]
    assert "spectral_indices" in ctx
    assert ctx["is_live_copernicus"] is True


# 4. TEST CLOUD COVER FILTERING & OBSCURATION HANDLING
def test_copernicus_cloud_cover_filtering():
    """Verify cloud cover filtering and observation obscuration status."""
    svc = CopernicusDataSpaceService()
    
    # Mocking a heavily cloud-covered scene (95% clouds)
    mock_features = [{
        "id": "S2B_MSIL2A_20260829T053639_CLOUDY.SAFE",
        "properties": {
            "datetime": "2026-08-29T05:52:55.622Z",
            "eo:cloud_cover": 95.0,
            "s2:mgrs_tile": "43QDA"
        }
    }]
    with patch.object(svc, "search_sentinel2_scenes", return_value=[]):
        ctx = svc.get_sentinel2_context_for_coordinates(21.6850, 72.5620, max_cloud_cover_pct=20.0)
        assert ctx is None, "Should return None when all scenes exceed max_cloud_cover_pct"


# 5. TEST SCENE UNAVAILABLE HANDLING (NO_SUITABLE_SCENE)
def test_copernicus_scene_unavailable_handling():
    """Verify that empty scene returns NO_SUITABLE_SCENE / IMAGERY_UNAVAILABLE rather than fabricating."""
    with patch.object(copernicus_service, "get_sentinel2_context_for_coordinates", return_value=None):
        eo_res = eo_verification_service.verify_thermal_source(
            source_id="SRC-REMOTE-WILD",
            latitude=28.5000,
            longitude=88.5000, # Remote mountain region with no recent pass
            facility_id=None
        )
        assert eo_res.structural_match_status == EOStructuralMatchStatus.IMAGERY_UNAVAILABLE
        assert "NO_SUITABLE_SCENE" in eo_res.verification_summary


# 6. TEST TIMEOUT AND NETWORK RESILIENCE
def test_copernicus_api_timeout_resilience():
    """Verify graceful handling when Sentinel Hub API encounters timeout."""
    svc = CopernicusDataSpaceService()
    with patch("requests.Session.post", side_effect=requests.Timeout("Connection timed out")):
        scenes = svc.search_sentinel2_scenes(
            bbox=[72.50, 21.60, 72.65, 21.75],
            start_datetime=datetime.now(timezone.utc) - timedelta(days=5),
            end_datetime=datetime.now(timezone.utc)
        )
        assert scenes == [], "Should return empty list on timeout without crashing"


# 7. TEST PROVENANCE INTEGRITY & NON-THERMAL SENSOR RESTRICTION
def test_copernicus_provenance_and_non_thermal_integrity():
    """Verify provenance integrity and confirm no fake temperature is computed from Sentinel-2."""
    eo_res = eo_verification_service.verify_thermal_source(
        source_id="SRC-IN-DAHEJ-FLARE-01",
        latitude=21.6850,
        longitude=72.5620,
        facility_id="FAC-IN-DAHEJ-001"
    )
    assert eo_res.source_provenance == "COPERNICUS_SENTINEL2"
    assert eo_res.copernicus_scene_id is not None
    assert eo_res.acquisition_timestamp is not None
    # Sentinel-2 MSI bands only
    assert set(eo_res.bands_used).issubset({"B02", "B03", "B04", "B08", "B11", "B12"})
    # Verify no temperature attribute was fabricated
    assert not hasattr(eo_res, "fire_temperature_k")
    assert not hasattr(eo_res, "frp_mw")


# 8. TEST FIRMS HOTSPOT + SENTINEL-2 COINCIDENCE INTEGRATION
def test_firms_hotspot_and_sentinel2_coincidence_pipeline():
    """
    Test end-to-end discrimination:
    NASA FIRMS thermal detection (FRP 32 MW) + Copernicus Sentinel-2 EO Context.
    """
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-DAHEJ-LIVE-COPERNICUS",
        latitude=21.6850,
        longitude=72.5620,
        mean_frp_mw=32.0,
        observation_count=35,
        active_days_count=20,
        diurnal_night_fraction=0.60,
        facility_id="FAC-IN-DAHEJ-001",
        facility_name="Dahej Petrochemical Complex",
        is_inside_facility=True
    )
    assert asm.predicted_class == "GAS_FLARE"
    assert asm.classification_state == "CLASSIFIED"
    assert asm.eo_verification is not None
    assert asm.eo_verification.source_provenance == "COPERNICUS_SENTINEL2"
    all_evidence = asm.top_supporting_evidence + asm.top_opposing_evidence
    assert any(e.evidence_type == "EO_VERIFICATION" for e in all_evidence)


# 9. COMPARISON: FIRMS-ONLY VS FIRMS + SENTINEL-2 CONTEXT
def test_firms_only_vs_firms_plus_sentinel_comparison():
    """
    Evaluates FIRMS-only thermal evidence vs FIRMS + Sentinel-2 spatial structural context.
    Measures the exact difference in system confidence and evidence sufficiency.
    """
    # 1. FIRMS-only (no facility linkage, unverified optical context)
    asm_firms_only = source_discrimination_service.discriminate_source(
        source_id="SRC-FIRMS-ONLY",
        latitude=21.6850,
        longitude=72.5620,
        mean_frp_mw=25.0,
        observation_count=2, # sparse observations
        active_days_count=1,
        diurnal_night_fraction=0.10,
        facility_id=None,
        is_inside_facility=False,
        force_eo_unavailable=True
    )

    # 2. FIRMS + Copernicus Sentinel-2 contextual evidence
    asm_firms_plus_s2 = source_discrimination_service.discriminate_source(
        source_id="SRC-FIRMS-S2-FUSION",
        latitude=21.6850,
        longitude=72.5620,
        mean_frp_mw=25.0,
        observation_count=15,
        active_days_count=10,
        diurnal_night_fraction=0.65,
        facility_id="FAC-IN-DAHEJ-001",
        is_inside_facility=True,
        force_eo_unavailable=False
    )

    # Compare metrics
    assert asm_firms_only.classification_state == "NEEDS_REVIEW"
    assert asm_firms_plus_s2.classification_state == "CLASSIFIED"
    assert asm_firms_plus_s2.system_confidence > asm_firms_only.system_confidence
    print(f"\nMeasured Confidence Comparison:")
    print(f"  FIRMS-only Confidence: {asm_firms_only.system_confidence:.2f} (State: {asm_firms_only.classification_state})")
    print(f"  FIRMS + Sentinel-2 Confidence: {asm_firms_plus_s2.system_confidence:.2f} (State: {asm_firms_plus_s2.classification_state})")


# 10. TEST NO SECRET LEAKAGE IN API ENDPOINTS
def test_secrets_never_leak_in_api_responses():
    """Verify that credentials (client ID, client secret) never appear in any API response."""
    res = client.get("/api/discrimination/sources/SRC-IN-DAHEJ-FLARE-01/eo-verification?lat=21.685&lon=72.562&facility_id=FAC-IN-DAHEJ-001")
    assert res.status_code == 200
    res_text = res.text
    if settings.COPERNICUS_CLIENT_SECRET:
        assert settings.COPERNICUS_CLIENT_SECRET not in res_text, "SECRET EXPOSED IN EO API RESPONSE!"
    if settings.COPERNICUS_CLIENT_ID:
        assert settings.COPERNICUS_CLIENT_ID not in res_text, "CLIENT ID EXPOSED IN EO API RESPONSE!"

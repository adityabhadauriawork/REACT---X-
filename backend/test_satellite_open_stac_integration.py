"""
Unit & Integration Test Suite for Free/Open Satellite Data Sources.
Tests:
1. Zero-credential startup (no private tokens required)
2. Public AWS Earth Search STAC fallback for Sentinel-2
3. Public Microsoft Planetary Computer STAC fallback for Landsat-8/9
4. Native local Planck blackbody physics estimator for VNF Nightfire
5. Schema compatibility across Sentinel2ContextResult, LandsatContextResult, and PlanckPhysicsResult
6. Evidence-Fusion & Confirmation Engine multi-source integration
7. Preservation of 23-feature ML classifier pipeline & metadata
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.satellite.copernicus_service import CopernicusDataSpaceService, copernicus_service
from app.services.satellite.landsat_service import LandsatM2MService, landsat_service
from app.services.satellite.vnf_service import EOGNightfireVNFService, vnf_service
from app.services.satellite.nightfire_service import NightfireService, nightfire_service
from app.services.satellite.confirmation_service import confirmation_service
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine
from app.services.ml.classifier_pipeline import pipeline, FEATURE_NAMES, CLASSES
from app.schemas.thermal import CanonicalThermalEvent

client = TestClient(app)


# =============================================================================
# 1. ZERO-CREDENTIAL CONFIGURATION & STARTUP TEST
# =============================================================================
def test_zero_credential_startup():
    """Verify services initialize cleanly with empty/unconfigured private credentials."""
    with patch.object(settings, "COPERNICUS_CLIENT_ID", ""), \
         patch.object(settings, "COPERNICUS_CLIENT_SECRET", ""), \
         patch.object(settings, "USGS_M2M_USERNAME", ""), \
         patch.object(settings, "USGS_M2M_TOKEN", ""), \
         patch.object(settings, "EOG_VNF_USERNAME", ""), \
         patch.object(settings, "EOG_VNF_PASSWORD", ""):
        
        c_svc = CopernicusDataSpaceService()
        l_svc = LandsatM2MService()
        v_svc = EOGNightfireVNFService()

        assert not c_svc.is_configured
        assert not l_svc.is_m2m_configured
        assert l_svc.is_configured  # Public Planetary Computer STAC is enabled by default
        assert v_svc.is_configured  # Local academic & Planck engine always available


# =============================================================================
# 2. SENTINEL-2 PUBLIC AWS EARTH SEARCH STAC FALLBACK TEST
# =============================================================================
def test_sentinel2_aws_earth_search_stac_fallback():
    """Verify Sentinel-2 falls back to zero-auth AWS Earth Search STAC when CDSE is not configured."""
    svc = CopernicusDataSpaceService()
    mock_stac_response = MagicMock()
    mock_stac_response.status_code = 200
    mock_stac_response.json.return_value = {
        "features": [
            {
                "id": "S2B_43QDA_20260901_0_L2A",
                "properties": {
                    "datetime": "2026-09-01T06:12:30Z",
                    "eo:cloud_cover": 12.5,
                    "s2:mgrs_tile": "43QDA"
                }
            }
        ]
    }

    with patch.object(settings, "COPERNICUS_CLIENT_ID", ""), \
         patch.object(settings, "COPERNICUS_CLIENT_SECRET", ""), \
         patch.object(svc._session, "post", return_value=mock_stac_response) as mock_post:
        
        scenes = svc.search_sentinel2_scenes(
            bbox=[72.5, 21.6, 72.6, 21.7],
            start_datetime=datetime.now(timezone.utc) - timedelta(days=10),
            end_datetime=datetime.now(timezone.utc)
        )
        assert len(scenes) == 1
        assert scenes[0]["id"] == "S2B_43QDA_20260901_0_L2A"
        # Confirm query went to public STAC endpoint
        assert "earth-search" in mock_post.call_args[0][0]


def test_sentinel2_context_schema_compatibility():
    """Verify Sentinel-2 context output dictionary schema compatibility."""
    svc = CopernicusDataSpaceService()
    mock_scene = {
        "id": "S2A_MSIL2A_20260830_TEST",
        "properties": {
            "datetime": "2026-08-30T06:00:00Z",
            "eo:cloud_cover": 8.0,
            "s2:mgrs_tile": "43QDA"
        }
    }
    with patch.object(svc, "search_sentinel2_scenes", return_value=[mock_scene]), \
         patch.object(svc, "fetch_sentinel2_multispectral_sample", return_value=None):
        ctx = svc.get_sentinel2_context_for_coordinates(latitude=21.6850, longitude=72.5620)
        assert ctx is not None
        assert ctx["source"] == "COPERNICUS_SENTINEL2"
        assert ctx["scene_id"] == "S2A_MSIL2A_20260830_TEST"
        assert "cloud_coverage_pct" in ctx
        assert "spatial_resolution_m" in ctx
        assert "bands_used" in ctx
        assert "spectral_indices" in ctx
        assert ctx["quality_status"] == "VALIDATED"


# =============================================================================
# 3. LANDSAT PUBLIC PLANETARY COMPUTER STAC FALLBACK TEST
# =============================================================================
def test_landsat_planetary_computer_stac_fallback():
    """Verify Landsat-8/9 falls back to zero-auth Planetary Computer STAC when USGS is not configured."""
    svc = LandsatM2MService()
    mock_stac_response = MagicMock()
    mock_stac_response.status_code = 200
    mock_stac_response.json.return_value = {
        "features": [
            {
                "id": "LC09_L2SP_148045_20260828_02_T1",
                "properties": {
                    "datetime": "2026-08-28T05:35:00Z",
                    "eo:cloud_cover": 4.2,
                    "platform": "landsat-9",
                    "landsat:wrs_path": 148,
                    "landsat:wrs_row": 45
                }
            }
        ]
    }

    with patch.object(settings, "USGS_M2M_USERNAME", ""), \
         patch.object(settings, "USGS_M2M_TOKEN", ""), \
         patch.object(svc._session, "post", return_value=mock_stac_response) as mock_post:
        
        scenes = svc.search_landsat_scenes(
            bbox=[72.5, 21.6, 72.6, 21.7],
            start_datetime=datetime.now(timezone.utc) - timedelta(days=15),
            end_datetime=datetime.now(timezone.utc)
        )
        assert len(scenes) == 1
        assert scenes[0]["id"] == "LC09_L2SP_148045_20260828_02_T1"
        # Confirm query went to planetary computer STAC endpoint
        assert "planetarycomputer" in mock_post.call_args[0][0]


def test_landsat_context_schema_compatibility():
    """Verify Landsat context output dictionary schema compatibility."""
    svc = LandsatM2MService()
    mock_scene = {
        "id": "LC09_L2SP_148045_20260828_02_T1",
        "properties": {
            "datetime": "2026-08-28T05:35:00Z",
            "eo:cloud_cover": 5.0,
            "platform": "landsat-9",
            "landsat:wrs_path": "148",
            "landsat:wrs_row": "045"
        }
    }
    with patch.object(svc, "search_landsat_scenes", return_value=[mock_scene]):
        ctx = svc.get_landsat_context_for_coordinates(latitude=21.6850, longitude=72.5620)
        assert ctx is not None
        assert ctx["source"] in ["USGS_LANDSAT_M2M", "USGS_LANDSAT_PLANETARY_COMPUTER"]
        assert ctx["satellite"] == "Landsat-9"
        assert ctx["scene_id"] == "LC09_L2SP_148045_20260828_02_T1"
        assert "thermal_calibration" in ctx
        assert ctx["quality_status"] in ["VALIDATED", "METADATA_ONLY"]


# =============================================================================
# 4. NATIVE PLANCK / VNF NIGHTFIRE ESTIMATOR TEST
# =============================================================================
def test_native_planck_estimator_execution():
    """Verify local Planck curve estimator executes accurately without commercial API calls."""
    evt = CanonicalThermalEvent(
        event_id="EVT-TEST-PLANCK-001",
        dedup_key="DEDUP-PLANCK-001",
        latitude=21.6850,
        longitude=72.5620,
        frp_mw=35.0,
        brightness_temp_k=365.0,
        source="NASA_FIRMS_VIIRS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS",
        acquisition_timestamp=datetime.now(timezone.utc),
        is_live_data=True
    )

    vnf_char = nightfire_service.characterize_thermal_source(evt)
    assert vnf_char is not None
    assert vnf_char.source_temperature_k >= 1000.0  # Combustion temperature in Kelvin
    assert vnf_char.radiant_heat_flux_w_m2 > 10000.0
    assert vnf_char.source_footprint_area_m2 > 0.0
    assert vnf_char.planck_curve_fit_quality > 0.90
    assert vnf_char.data_mode == "ACADEMIC DATA / OFFLINE VALIDATION"


# =============================================================================
# 5. EVIDENCE FUSION & CONFIRMATION COMPATIBILITY TEST
# =============================================================================
def test_evidence_fusion_with_open_sources():
    """Verify confirmation_service and eo_verification_service work with open sources."""
    evt = CanonicalThermalEvent(
        event_id="EVT-TEST-OPEN-001",
        dedup_key="DEDUP-OPEN-001",
        latitude=21.6850,
        longitude=72.5620,
        frp_mw=45.0,
        brightness_temp_k=375.0,
        source="NASA_FIRMS_VIIRS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS",
        acquisition_timestamp=datetime.now(timezone.utc),
        is_live_data=True
    )

    summary = confirmation_service.characterize_and_confirm(evt)
    assert summary is not None
    assert summary.event_id == "EVT-TEST-OPEN-001"
    assert summary.overall_corroboration_score > 0.50
    assert summary.corroborating_sensors_count >= 1
    assert summary.viirs_nightfire_confirmed is True


# =============================================================================
# 6. ML CLASSIFIER UNCHANGED & 23-FEATURE INTEGRITY TEST
# =============================================================================
def test_ml_classifier_23_features_and_classes_integrity():
    """Confirm 23-feature vector and 7-class taxonomy are untouched."""
    assert len(FEATURE_NAMES) == 23
    assert len(CLASSES) == 7
    expected_classes = [
        "AGRICULTURAL_BURNING",
        "GAS_FLARE",
        "INDUSTRIAL_FIRE",
        "MINING_PROCESS_HEAT",
        "OTHER_UNKNOWN",
        "ROUTINE_PROCESS_HEAT",
        "WILDFIRE_NATURAL"
    ]
    assert sorted(CLASSES) == sorted(expected_classes)

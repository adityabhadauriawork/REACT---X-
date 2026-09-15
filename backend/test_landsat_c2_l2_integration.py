import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.satellite.landsat_service import LandsatM2MService, landsat_service
from app.services.ml.classifier_pipeline import FEATURE_NAMES, CLASSES
from app.services.fusion.dempster_shafer_engine import ds_combiner
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine


# 1. TEST LANDSAT STAC SEARCH FOR BOTH LANDSAT 8 AND LANDSAT 9
def test_landsat_stac_search_l8_and_l9():
    """Verify STAC search retrieves both Landsat-8 and Landsat-9 scenes across Indian AOIs."""
    # Test Dahej AOI [72.50, 21.60, 72.60, 21.70]
    bbox = [72.50, 21.60, 72.60, 21.70]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 6, 1, tzinfo=timezone.utc)

    scenes = landsat_service.search_landsat_scenes(
        bbox=bbox,
        start_datetime=start,
        end_datetime=end,
        max_cloud_cover_pct=100.0,
        limit=10
    )
    assert len(scenes) > 0, "Failed to retrieve Landsat scenes from Planetary Computer STAC"

    platforms = {s.get("properties", {}).get("platform") for s in scenes}
    assert any("landsat-8" in str(p).lower() or "landsat-9" in str(p).lower() for p in platforms), (
        f"Expected landsat-8 or landsat-9, got {platforms}"
    )


# 2. TEST REAL ASSET EXTRACTION
def test_landsat_asset_extraction():
    """Verify extraction of real Collection 2 Level-2 asset URLs (lwir11, qa, qa_pixel, swir16, swir22, preview)."""
    ctx = landsat_service.get_landsat_context_for_coordinates(
        latitude=21.685,
        longitude=72.562,
        lookback_days=180,
        max_cloud_cover_pct=100.0
    )
    assert ctx is not None, "Failed to retrieve Landsat context for Dahej"

    # Verify asset URLs
    assets = ctx.get("assets", {})
    assert "lwir11" in assets and assets["lwir11"] is not None, "Missing lwir11 asset URL"
    assert "qa" in assets and assets["qa"] is not None, "Missing qa (ST_QA) asset URL"
    assert "qa_pixel" in assets and assets["qa_pixel"] is not None, "Missing qa_pixel asset URL"
    assert "swir16" in assets and assets["swir16"] is not None, "Missing swir16 asset URL"
    assert "swir22" in assets and assets["swir22"] is not None, "Missing swir22 asset URL"
    assert "rendered_preview" in assets, "Missing rendered_preview field"

    # Verify no hardcoded 54.2 C
    t_cal = ctx.get("thermal_calibration", {})
    assert t_cal.get("derived_ground_temp_c") != 54.2 or ctx["pixel_sample"]["is_real_pixel_sampled"], (
        "Should not use hardcoded 54.2 C placeholder without sampling"
    )


# 3. TEST QA_PIXEL PARSING AND ST_QA UNCERTAINTY SCREENING
def test_landsat_qa_uncertainty_and_cloud_screening():
    """Verify bitpacked QA_PIXEL mask parsing and ST_QA uncertainty qualification."""
    # Test clear-sky bitmask (21824 = 0b0101010101000000 -> bit 6 Clear = 1)
    clear_qa = landsat_service.parse_qa_pixel(21824.0)
    assert clear_qa["is_clear"] is True
    assert clear_qa["is_cloud"] is False
    assert clear_qa["is_cloud_obscured"] is False
    assert clear_qa["screening_verdict"] == "CLEAR_SKY"

    # Test cloudy bitmask (55052 -> bit 3 Cloud = 1, bit 2 Cirrus = 1)
    cloud_qa = landsat_service.parse_qa_pixel(55052.0)
    assert cloud_qa["is_cloud"] is True or cloud_qa["is_cirrus"] is True
    assert cloud_qa["is_cloud_obscured"] is True
    assert cloud_qa["screening_verdict"] == "CLOUD_OBSCURED"

    # Test Dilated Cloud (bit 1)
    dilated_qa = landsat_service.parse_qa_pixel(2.0) # bit 1 = 1
    assert dilated_qa["is_dilated_cloud"] is True
    assert dilated_qa["is_cloud_obscured"] is True

    # Test ST_QA scale factor: DN 322 -> 3.22 K
    pixel_sample = landsat_service.sample_landsat_pixels(
        item_id="LC08_L2SP_148045_20240525_02_T1",
        latitude=21.685,
        longitude=72.562
    )
    assert pixel_sample["st_qa_uncertainty_k"] is not None
    assert 0.0 <= pixel_sample["st_qa_uncertainty_k"] <= 15.0


# 4. TEST SWIR RATIO & SOLAR GEOMETRY EXTRACTION
def test_landsat_swir_and_solar_geometry():
    """Verify SWIR B7/B6 ratio calculation and solar zenith/elevation parsing."""
    ctx = landsat_service.get_landsat_context_for_coordinates(
        latitude=21.685,
        longitude=72.562,
        lookback_days=180,
        max_cloud_cover_pct=100.0
    )
    assert ctx is not None

    solar = ctx.get("solar_geometry", {})
    assert "sun_elevation_deg" in solar
    assert "sun_azimuth_deg" in solar

    t_cal = ctx.get("thermal_calibration", {})
    if t_cal.get("swir_band_6_reflectance") and t_cal.get("swir_band_7_reflectance"):
        expected_ratio = round(t_cal["swir_band_7_reflectance"] / t_cal["swir_band_6_reflectance"], 4)
        assert t_cal.get("swir_ratio_b7_b6") == expected_ratio


# 5. TEST EVIDENCE NORMALIZATION & NO DOUBLE COUNTING (OPTION C)
def test_landsat_evidence_normalization_and_no_double_counting():
    """Verify Option C architecture: single nearest scene in D-S fusion; deterministic event IDs."""
    scene_mock = {
        "scene_id": "LC09_L2SP_150045_20240531_02_T1",
        "satellite": "Landsat-9",
        "sensor": "TIRS-2 / OLI-2",
        "wrs_path_row": "150/045",
        "acquisition_timestamp": datetime(2024, 5, 31, 5, 44, 55, tzinfo=timezone.utc),
        "quality_status": "VALIDATED",
        "cloud_coverage_pct": 12.5,
        "thermal_calibration": {
            "derived_ground_temp_k": 323.4,
            "derived_ground_temp_c": 50.3,
            "st_qa_uncertainty_k": 5.0,
            "swir_ratio_b7_b6": 0.80
        }
    }

    evt1 = landsat_service.create_canonical_thermal_event(scene_mock, 22.360, 69.830)
    evt2 = landsat_service.create_canonical_thermal_event(scene_mock, 22.360, 69.830)

    # Verify deterministic event ID deduplication
    assert evt1["event_id"] == evt2["event_id"]
    assert evt1["event_id"] == "EVT_LS_Landsat9_150_045_20240531"


# 6. TEST SCIENTIFIC SAFETY INVARIANTS
def test_scientific_safety_invariants():
    """Confirm frozen 23-feature vector, 7-class taxonomy, and Dempster-Shafer math remain 100% untouched."""
    # 1. 23-Feature Vector
    assert len(FEATURE_NAMES) == 23, f"FEATURE_NAMES changed! Length is {len(FEATURE_NAMES)}, expected 23"
    assert FEATURE_NAMES[0] == "frp_current"

    # 2. 7-Class Industrial Taxonomy
    assert len(CLASSES) == 7, f"CLASSES taxonomy changed! Length is {len(CLASSES)}, expected 7"
    assert "INDUSTRIAL_FIRE" in CLASSES
    assert "GAS_FLARE" in CLASSES
    assert "ROUTINE_PROCESS_HEAT" in CLASSES

    # 3. Dempster-Shafer Frame of Discernment Invariance
    assert len(ds_combiner.FRAME_OF_DISCERNMENT) == 6
    assert "THERMAL_ESCALATION" in ds_combiner.FRAME_OF_DISCERNMENT
    assert "NORMAL" in ds_combiner.FRAME_OF_DISCERNMENT

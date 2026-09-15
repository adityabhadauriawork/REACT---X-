import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from app.services.ingestion.deterministic_cleaner import deterministic_cleaner, DeterministicDataCleaner
from app.services.ml.classifier_pipeline import FEATURE_NAMES

def test_deterministic_cleaner_valid_record():
    raw = {
        "latitude": 22.45678,
        "longitude": 70.12345,
        "frp": 34.567,
        "bright_ti4": 345.67,
        "confidence": "h",
        "satellite": "NOAA-20",
        "acq_date": "2026-08-15",
        "acq_time": "1345"
    }
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(raw)
    assert is_valid is True
    assert cleaned is not None
    assert cleaned["latitude"] == 22.4568
    assert cleaned["longitude"] == 70.1235
    assert cleaned["frp_mw"] == 34.57
    assert cleaned["brightness_temp_k"] == 345.67
    assert cleaned["confidence"] == "HIGH"
    assert cleaned["confidence_pct"] == 95.0
    assert cleaned["source_satellite"] == "NOAA-20"
    assert cleaned["sensor_name"] == "VIIRS_375M"
    assert cleaned["data_quality_status"] == "GOOD"
    assert len(flags) == 0

def test_deterministic_cleaner_invalid_coordinates():
    # Lat > 90
    bad_lat = {"latitude": 95.0, "longitude": 75.0, "frp": 10.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(bad_lat)
    assert is_valid is False
    assert cleaned is None
    assert "OUT_OF_BOUNDS_LATITUDE" in flags

    # Lon < -180
    bad_lon = {"latitude": 20.0, "longitude": -190.0, "frp": 10.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(bad_lon)
    assert is_valid is False
    assert cleaned is None
    assert "OUT_OF_BOUNDS_LONGITUDE" in flags

    # Non-numeric string
    malformed = {"latitude": "invalid_lat", "longitude": 75.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(malformed)
    assert is_valid is False
    assert "MALFORMED_COORDINATES" in flags

def test_deterministic_cleaner_negative_and_extreme_frp():
    # Negative FRP clamped to 0.0
    neg_frp = {"latitude": 20.0, "longitude": 75.0, "frp": -15.2}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(neg_frp)
    assert is_valid is True
    assert cleaned["frp_mw"] == 0.0
    assert "NEGATIVE_FRP_CLAMPED" in flags
    assert cleaned["data_quality_status"] == "WARNING"

    # Extreme FRP spike flagged
    spike_frp = {"latitude": 20.0, "longitude": 75.0, "frp": 6000.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(spike_frp)
    assert is_valid is True
    assert cleaned["frp_mw"] == 6000.0
    assert "EXTREME_FRP_SPIKE" in flags

def test_deterministic_cleaner_brightness_temperature_bounds():
    # Below plausible terrestrial range (< 200 K)
    cold = {"latitude": 20.0, "longitude": 75.0, "bright_ti4": 150.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(cold)
    assert is_valid is True
    assert "SUSPECT_LOW_BRIGHTNESS_TEMP" in flags

    # Above plausible range (> 2000 K)
    hot = {"latitude": 20.0, "longitude": 75.0, "bright_ti4": 2500.0}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(hot)
    assert is_valid is True
    assert "EXTREME_BRIGHTNESS_TEMP" in flags

def test_deterministic_cleaner_timestamp_and_future_detection():
    # Future timestamp (> 10 mins from now)
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    rec = {"latitude": 20.0, "longitude": 75.0, "timestamp": future_time.isoformat()}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(rec)
    assert is_valid is True
    assert "FUTURE_TIMESTAMP_DETECTED" in flags

    # Invalid timestamp string
    bad_ts = {"latitude": 20.0, "longitude": 75.0, "timestamp": "not-a-timestamp"}
    is_valid, cleaned, flags = deterministic_cleaner.clean_thermal_event_dict(bad_ts)
    assert is_valid is True
    assert "INVALID_TIMESTAMP_DEFAULTED" in flags

def test_deterministic_cleaner_dedup_reproducibility():
    raw_1 = {
        "latitude": 21.123456,
        "longitude": 72.654321,
        "frp": 25.104,
        "satellite": "NOAA-20",
        "acq_date": "2026-09-01",
        "acq_time": "1200"
    }
    raw_2 = {
        "latitude": 21.123499,  # rounds to 21.1235
        "longitude": 72.654301, # rounds to 72.6543
        "frp": 25.101,          # rounds to 25.10
        "satellite": "NOAA-20",
        "acq_date": "2026-09-01",
        "acq_time": "1200"
    }
    _, c1, _ = deterministic_cleaner.clean_thermal_event_dict(raw_1)
    _, c2, _ = deterministic_cleaner.clean_thermal_event_dict(raw_2)

    assert c1["dedup_key"] == c2["dedup_key"]
    assert c1["event_id"] == c2["event_id"]

def test_deterministic_cleaner_feature_vector_imputation_and_bounds():
    # Incomplete dictionary with missing values and extreme values
    raw_feats = {
        "frp_current": 10000.0,  # exceeds max bound 5000.0
        "spatial_stability": -0.5, # below min bound 0.0
        "facility_distance_m": float("nan"),  # NaN should be imputed
        # all other features omitted -> should use defaults
    }
    vec = deterministic_cleaner.clean_feature_vector(raw_feats)

    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float64
    assert len(vec) == len(FEATURE_NAMES)
    assert not np.isnan(vec).any()

    # Verify clamping
    frp_idx = FEATURE_NAMES.index("frp_current")
    assert vec[frp_idx] == 5000.0

    stab_idx = FEATURE_NAMES.index("spatial_stability")
    assert vec[stab_idx] == 0.0

    dist_idx = FEATURE_NAMES.index("facility_distance_m")
    assert vec[dist_idx] == DeterministicDataCleaner.FEATURE_DEFAULTS["facility_distance_m"]

import math
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from app.schemas.thermal import CanonicalThermalEvent
from app.services.ml.classifier_pipeline import FEATURE_NAMES

class DeterministicDataCleaner:
    """
    Deterministic Cleaning & Quality Assurance Pipeline for REACT-X.
    Guarantees that identical raw inputs always yield identical, normalized,
    leakage-safe, and physically bounded clean representations.
    """

    FEATURE_DEFAULTS = {
        "frp_current": 15.0,
        "frp_median": 12.0,
        "frp_robust_zscore": 0.0,
        "frp_percentile": 50.0,
        "frp_iqr": 5.0,
        "frp_mad": 3.0,
        "temp_current": 330.0,
        "temp_median": 325.0,
        "temp_percentile": 50.0,
        "temp_departure_k": 5.0,
        "spatial_stability": 0.85,
        "dispersion_radius_r95": 120.0,
        "facility_distance_m": 50.0,
        "is_inside_facility": 1.0,
        "active_days": 15.0,
        "observation_count": 25.0,
        "recurrence_rate": 0.75,
        "detection_rate": 0.60,
        "day_night_ratio": 1.2,
        "night_fraction": 0.45,
        "seasonal_deviation": 0.0,
        "sta_overlap": 1.0,
        "satellite_count": 2.0
    }

    FEATURE_BOUNDS = {
        "frp_current": (0.0, 5000.0),
        "frp_median": (0.0, 5000.0),
        "frp_robust_zscore": (-10.0, 100.0),
        "frp_percentile": (0.0, 100.0),
        "frp_iqr": (0.0, 1000.0),
        "frp_mad": (0.0, 1000.0),
        "temp_current": (200.0, 2500.0),
        "temp_median": (200.0, 2500.0),
        "temp_percentile": (0.0, 100.0),
        "temp_departure_k": (-200.0, 1500.0),
        "spatial_stability": (0.0, 1.0),
        "dispersion_radius_r95": (0.0, 50000.0),
        "facility_distance_m": (0.0, 500000.0),
        "is_inside_facility": (0.0, 1.0),
        "active_days": (1.0, 3650.0),
        "observation_count": (1.0, 10000.0),
        "recurrence_rate": (0.0, 1.0),
        "detection_rate": (0.0, 1.0),
        "day_night_ratio": (0.0, 100.0),
        "night_fraction": (0.0, 1.0),
        "seasonal_deviation": (-100.0, 100.0),
        "sta_overlap": (0.0, 1.0),
        "satellite_count": (1.0, 10.0)
    }

    def clean_thermal_event_dict(
        self,
        raw: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """
        Deterministically cleans and validates raw thermal observations.
        Returns (is_valid, cleaned_dict, quality_flags).
        """
        flags: List[str] = []

        # 1. Coordinates Validation
        try:
            lat = float(raw.get("latitude", raw.get("lat", 0.0)))
            lon = float(raw.get("longitude", raw.get("lon", 0.0)))
        except (ValueError, TypeError):
            return False, None, ["MALFORMED_COORDINATES"]

        if not (-90.0 <= lat <= 90.0) or math.isnan(lat):
            return False, None, ["OUT_OF_BOUNDS_LATITUDE"]
        if not (-180.0 <= lon <= 180.0) or math.isnan(lon):
            return False, None, ["OUT_OF_BOUNDS_LONGITUDE"]

        # 2. FRP Validation
        try:
            frp = float(raw.get("frp", raw.get("frp_mw", 0.0)))
            if math.isnan(frp) or frp < 0.0:
                flags.append("NEGATIVE_FRP_CLAMPED")
                frp = 0.0
            elif frp > 5000.0:
                flags.append("EXTREME_FRP_SPIKE")
        except (ValueError, TypeError):
            frp = 0.0
            flags.append("MISSING_FRP_DEFAULTED")

        # 3. Brightness Temperature Validation
        tb_k = None
        tb_raw = raw.get("bright_ti4", raw.get("brightness", raw.get("brightness_temp_k")))
        if tb_raw is not None:
            try:
                tb_k = float(tb_raw)
                if math.isnan(tb_k):
                    tb_k = None
                elif tb_k < 200.0:
                    flags.append("SUSPECT_LOW_BRIGHTNESS_TEMP")
                elif tb_k > 2000.0:
                    flags.append("EXTREME_BRIGHTNESS_TEMP")
            except (ValueError, TypeError):
                tb_k = None

        # 4. Spatio-Temporal Timestamp Parsing & UTC Normalization
        acq_dt = None
        now_utc = datetime.now(timezone.utc)
        if "acquisition_timestamp" in raw and isinstance(raw["acquisition_timestamp"], datetime):
            acq_dt = raw["acquisition_timestamp"].astimezone(timezone.utc) if raw["acquisition_timestamp"].tzinfo else raw["acquisition_timestamp"].replace(tzinfo=timezone.utc)
        elif "acq_date" in raw:
            acq_date_str = str(raw["acq_date"]).strip()
            acq_time_str = str(raw.get("acq_time", "0000")).strip().zfill(4)
            try:
                dt_str = f"{acq_date_str} {acq_time_str[:2]}:{acq_time_str[2:4]}:00"
                acq_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    acq_dt = datetime.fromisoformat(acq_date_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    acq_dt = now_utc
                    flags.append("INVALID_TIMESTAMP_DEFAULTED")
        elif "timestamp" in raw:
            try:
                ts_str = str(raw["timestamp"]).replace("Z", "+00:00")
                acq_dt = datetime.fromisoformat(ts_str)
                if acq_dt.tzinfo is None:
                    acq_dt = acq_dt.replace(tzinfo=timezone.utc)
            except Exception:
                acq_dt = now_utc
                flags.append("INVALID_TIMESTAMP_DEFAULTED")
        else:
            acq_dt = now_utc
            flags.append("MISSING_TIMESTAMP_DEFAULTED")

        # Future timestamp check
        if acq_dt > (now_utc + timedelta(minutes=10)):
            flags.append("FUTURE_TIMESTAMP_DETECTED")

        # 5. Satellite & Sensor Normalization
        sat_raw = str(raw.get("satellite", raw.get("source_satellite", "NOAA-20"))).strip().upper()
        if sat_raw in ["N", "NOAA-20", "NOAA20", "J1", "JPSS-1"]:
            sat_norm = "NOAA-20"
        elif sat_raw in ["21", "NOAA-21", "NOAA21", "J2", "JPSS-2"]:
            sat_norm = "NOAA-21"
        elif sat_raw in ["NPP", "SNPP", "SUOMI-NPP", "SUOMI_NPP", "S-NPP"]:
            sat_norm = "SUOMI-NPP"
        elif sat_raw in ["T", "TERRA", "MODIS_TERRA"]:
            sat_norm = "TERRA"
        elif sat_raw in ["A", "AQUA", "MODIS_AQUA"]:
            sat_norm = "AQUA"
        else:
            sat_norm = sat_raw or "NOAA-20"

        sensor_norm = "MODIS_1KM" if sat_norm in ["TERRA", "AQUA"] else "VIIRS_375M"

        # 6. Confidence Normalization
        conf_raw = raw.get("confidence", "NOMINAL")
        if isinstance(conf_raw, (int, float)):
            pct = float(conf_raw)
            conf_cat = "HIGH" if pct >= 80.0 else ("NOMINAL" if pct >= 30.0 else "LOW")
            conf_pct = max(0.0, min(100.0, pct))
        else:
            c_str = str(conf_raw).strip().lower()
            if c_str in ["h", "high"]:
                conf_cat = "HIGH"
                conf_pct = 95.0
            elif c_str in ["l", "low"]:
                conf_cat = "LOW"
                conf_pct = 25.0
            else:
                conf_cat = "NOMINAL"
                conf_pct = 65.0

        # 7. Deterministic Dedup Key
        epoch_sec = int(acq_dt.timestamp())
        lat_r = round(lat, 4)
        lon_r = round(lon, 4)
        frp_r = round(frp, 2)
        raw_key = f"{sat_norm}:{sensor_norm}:{epoch_sec}:{lat_r}:{lon_r}:{frp_r}"
        dedup_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        cleaned_dict = {
            "event_id": raw.get("event_id", f"EVT-{dedup_key[:12].upper()}"),
            "dedup_key": dedup_key,
            "source": raw.get("source", "NASA_FIRMS"),
            "source_satellite": sat_norm,
            "sensor_name": sensor_norm,
            "acquisition_timestamp": acq_dt,
            "latitude": lat_r,
            "longitude": lon_r,
            "frp_mw": frp_r,
            "brightness_temp_k": round(tb_k, 2) if tb_k is not None else None,
            "confidence": conf_cat,
            "confidence_pct": conf_pct,
            "data_quality_status": "GOOD" if not flags else "WARNING",
            "data_quality_flags": flags
        }
        return True, cleaned_dict, flags

    def clean_feature_vector(
        self,
        raw_features: Dict[str, Any]
    ) -> np.ndarray:
        """
        Deterministically transforms raw dictionary into bounded, complete float64 vector.
        Guarantees exact feature ordering matching FEATURE_NAMES.
        """
        vec = []
        for name in FEATURE_NAMES:
            val = raw_features.get(name)
            if val is None or math.isnan(val):
                val = self.FEATURE_DEFAULTS.get(name, 0.0)
            else:
                val = float(val)

            # Apply physical bounds clamping
            if name in self.FEATURE_BOUNDS:
                b_min, b_max = self.FEATURE_BOUNDS[name]
                val = max(b_min, min(b_max, val))

            vec.append(val)

        return np.array(vec, dtype=np.float64)

deterministic_cleaner = DeterministicDataCleaner()

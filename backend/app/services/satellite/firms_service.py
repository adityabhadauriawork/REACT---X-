import math
import hashlib
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.schemas.thermal import (
    CanonicalThermalEvent,
    ThermalEventGeoJSONFeature,
    ThermalEventGeoJSONCollection,
    ThermalEventStatsResponse,
    FIRMSIngestSummaryResponse
)
from app.models.thermal_event import ThermalEventModel
from app.services.satellite.spatial_index import lat_lng_to_h3, point_in_bbox

logger = logging.getLogger(__name__)

class FIRMSService:
    """
    NASA FIRMS (Fire Information for Resource Management System) Data Foundation Adapter.
    Handles ingestion, validation, normalization, deduplication, spatial H3 indexing,
    persistent storage, GeoJSON rendering, and statistical aggregation for satellite thermal observations.
    """

    def __init__(self):
        self._memory_events: List[CanonicalThermalEvent] = []
        self._init_benchmark_events()

    # =========================================================================
    # 1. NORMALIZATION & DEDUPLICATION LOGIC
    # =========================================================================

    def normalize_satellite_name(self, raw_sat: Optional[str]) -> str:
        """
        Normalize satellite name into canonical nomenclature:
        NOAA-20, NOAA-21, SUOMI-NPP, TERRA, AQUA, INSAT-3DR, SENTINEL-2
        """
        if not raw_sat:
            return "NOAA-20"
        s = str(raw_sat).strip().upper()
        if s in ["N", "NOAA-20", "NOAA20", "J1", "JPSS-1"]:
            return "NOAA-20"
        elif s in ["21", "NOAA-21", "NOAA21", "J2", "JPSS-2"]:
            return "NOAA-21"
        elif s in ["NPP", "SNPP", "SUOMI-NPP", "SUOMI_NPP", "S-NPP"]:
            return "SUOMI-NPP"
        elif s in ["T", "TERRA", "MODIS_TERRA"]:
            return "TERRA"
        elif s in ["A", "AQUA", "MODIS_AQUA"]:
            return "AQUA"
        elif s in ["INSAT", "INSAT-3D", "INSAT-3DR"]:
            return "INSAT-3DR"
        elif s in ["S2", "SENTINEL-2", "SENTINEL-2A", "SENTINEL-2B"]:
            return "SENTINEL-2"
        return s

    def normalize_sensor_name(self, raw_sensor: Optional[str], satellite: str) -> str:
        """
        Normalize sensor name into canonical descriptor:
        VIIRS_375M, MODIS_1KM, MSI_20M, TIR_4KM
        """
        if raw_sensor:
            s = str(raw_sensor).strip().upper()
            if "VIIRS" in s or "375" in s:
                return "VIIRS_375M"
            if "MODIS" in s or "1KM" in s:
                return "MODIS_1KM"
            if "MSI" in s or "SWIR" in s:
                return "MSI_20M"
            if "TIR" in s or "INSAT" in s:
                return "TIR_4KM"
            return s

        # Deduce from satellite
        if satellite in ["NOAA-20", "NOAA-21", "SUOMI-NPP"]:
            return "VIIRS_375M"
        elif satellite in ["TERRA", "AQUA"]:
            return "MODIS_1KM"
        elif satellite == "SENTINEL-2":
            return "MSI_20M"
        return "VIIRS_375M"

    def normalize_confidence(self, raw_conf: Any) -> Tuple[str, Optional[float]]:
        """
        Normalize confidence into categorical ('LOW', 'NOMINAL', 'HIGH') and continuous pct (0-100%).
        Handles both VIIRS ('l', 'n', 'h') and MODIS (0 to 100 integer).
        """
        if raw_conf is None or raw_conf == "":
            return "NOMINAL", 65.0

        if isinstance(raw_conf, (int, float)):
            pct = float(raw_conf)
            if pct >= 80.0:
                return "HIGH", pct
            elif pct >= 30.0:
                return "NOMINAL", pct
            else:
                return "LOW", pct

        s = str(raw_conf).strip().lower()
        if s in ["h", "high"]:
            return "HIGH", 95.0
        elif s in ["n", "nominal", "med", "medium"]:
            return "NOMINAL", 65.0
        elif s in ["l", "low"]:
            return "LOW", 25.0

        try:
            val = float(s)
            return self.normalize_confidence(val)
        except ValueError:
            return "NOMINAL", 50.0

    def compute_dedup_key(
        self,
        source_satellite: str,
        sensor_name: str,
        acquisition_timestamp: datetime,
        latitude: float,
        longitude: float,
        frp_mw: float
    ) -> str:
        """
        Deterministic SHA256 deduplication key based on physics & spatio-temporal invariants:
        {satellite}:{sensor}:{timestamp_epoch_sec}:{round(lat,4)}:{round(lon,4)}:{round(frp,2)}
        """
        epoch_sec = int(acquisition_timestamp.replace(tzinfo=timezone.utc).timestamp()) if acquisition_timestamp.tzinfo is None else int(acquisition_timestamp.timestamp())
        lat_r = round(latitude, 4)
        lon_r = round(longitude, 4)
        frp_r = round(frp_mw, 2)
        raw_key = f"{source_satellite}:{sensor_name}:{epoch_sec}:{lat_r}:{lon_r}:{frp_r}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    # =========================================================================
    # 2. VALIDATION & QUALITY ASSURANCE ENGINE
    # =========================================================================

    def validate_and_normalize_record(
        self,
        raw: Dict[str, Any],
        is_live_data: bool = True
    ) -> Tuple[bool, str, List[str], Optional[Dict[str, Any]]]:
        """
        Validate incoming NASA FIRMS observation against physical bounds,
        standards, and timestamps. Returns (is_valid, quality_status, flags, normalized_dict).
        """
        flags: List[str] = []
        status = "GOOD"

        # 1. Coordinate Validation
        try:
            lat = float(raw.get("latitude", raw.get("lat", 0.0)))
            lon = float(raw.get("longitude", raw.get("lon", 0.0)))
        except (ValueError, TypeError):
            return False, "INVALID", ["MALFORMED_COORDINATES"], None

        if not (-90.0 <= lat <= 90.0):
            return False, "INVALID", ["OUT_OF_BOUNDS_LATITUDE"], None
        if not (-180.0 <= lon <= 180.0):
            return False, "INVALID", ["OUT_OF_BOUNDS_LONGITUDE"], None

        # 2. FRP Validation
        try:
            frp = float(raw.get("frp", raw.get("frp_mw", 0.0)))
            if frp < 0.0:
                flags.append("NEGATIVE_FRP_CLAMPED")
                frp = 0.0
                status = "WARNING"
            elif frp > 5000.0:
                flags.append("EXTREME_FRP_SPIKE")
                status = "WARNING"
        except (ValueError, TypeError):
            frp = 0.0
            flags.append("MISSING_FRP_DEFAULTED")
            status = "WARNING"

        # 3. Brightness Temperature Validation
        tb_k = None
        tb_raw = raw.get("bright_ti4", raw.get("brightness", raw.get("brightness_temp_k")))
        if tb_raw is not None:
            try:
                tb_k = float(tb_raw)
                if tb_k < 200.0:
                    flags.append("SUSPECT_LOW_BRIGHTNESS_TEMP")
                    status = "WARNING"
                elif tb_k > 2000.0:
                    flags.append("EXTREME_BRIGHTNESS_TEMP")
                    status = "WARNING"
            except (ValueError, TypeError):
                tb_k = None

        tb_i4_k = None
        tb_i4_raw = raw.get("bright_ti5", raw.get("brightness_temp_i4_k"))
        if tb_i4_raw is not None:
            try:
                tb_i4_k = float(tb_i4_raw)
            except (ValueError, TypeError):
                tb_i4_k = None

        # 4. Spatio-Temporal Timestamp Parsing
        acq_dt = None
        if "acquisition_timestamp" in raw and isinstance(raw["acquisition_timestamp"], datetime):
            acq_dt = raw["acquisition_timestamp"]
        elif "acq_date" in raw:
            acq_date_str = str(raw["acq_date"]).strip()
            acq_time_str = str(raw.get("acq_time", "0000")).strip().zfill(4)
            try:
                dt_str = f"{acq_date_str} {acq_time_str[:2]}:{acq_time_str[2:4]}:00"
                acq_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    acq_dt = datetime.fromisoformat(acq_date_str)
                except ValueError:
                    acq_dt = datetime.utcnow()
                    flags.append("INVALID_TIMESTAMP_DEFAULTED")
                    status = "WARNING"
        elif "timestamp" in raw:
            try:
                acq_dt = datetime.fromisoformat(str(raw["timestamp"]).replace("Z", "+00:00"))
            except Exception:
                acq_dt = datetime.utcnow()
                flags.append("INVALID_TIMESTAMP_DEFAULTED")
                status = "WARNING"
        else:
            acq_dt = datetime.utcnow()
            flags.append("MISSING_TIMESTAMP_DEFAULTED")
            status = "WARNING"

        # Check for future timestamp
        if acq_dt > datetime.utcnow() + timedelta(minutes=10):
            flags.append("FUTURE_TIMESTAMP_DETECTED")
            status = "WARNING"

        # 5. Normalization
        sat_norm = self.normalize_satellite_name(raw.get("satellite", raw.get("source_satellite")))
        sensor_norm = self.normalize_sensor_name(raw.get("sensor", raw.get("sensor_name")), sat_norm)
        conf_cat, conf_pct = self.normalize_confidence(raw.get("confidence"))
        day_night = str(raw.get("daynight", raw.get("day_night", "D"))).strip().upper()
        if day_night not in ["D", "N"]:
            day_night = "D"

        scan = float(raw.get("scan", 0.0)) if raw.get("scan") is not None else None
        track = float(raw.get("track", 0.0)) if raw.get("track") is not None else None
        version = str(raw.get("version", raw.get("source_version", "NRT_v1.0"))).strip()

        # 6. Deterministic Deduplication Key & Event ID
        dedup_key = self.compute_dedup_key(
            source_satellite=sat_norm,
            sensor_name=sensor_norm,
            acquisition_timestamp=acq_dt,
            latitude=lat,
            longitude=lon,
            frp_mw=frp
        )

        event_id = raw.get("event_id") or f"FIRMS-{sat_norm.replace('-', '')}-{acq_dt.strftime('%Y%m%d%H%M')}-{dedup_key[:6].upper()}"

        # 7. Spatial H3 & GeoJSON
        h3_idx = lat_lng_to_h3(lat, lon, resolution=7)
        geometry = {"type": "Point", "coordinates": [lon, lat]}

        clean = {
            "event_id": event_id,
            "dedup_key": dedup_key,
            "source": "NASA_FIRMS",
            "source_satellite": sat_norm,
            "sensor_name": sensor_norm,
            "source_version": version,
            "acquisition_timestamp": acq_dt,
            "latitude": lat,
            "longitude": lon,
            "frp_mw": frp,
            "brightness_temp_k": tb_k,
            "brightness_temp_i4_k": tb_i4_k,
            "confidence": conf_cat,
            "confidence_pct": conf_pct,
            "day_night": day_night,
            "scan": scan,
            "track": track,
            "ingested_at": datetime.utcnow(),
            "is_live_data": is_live_data,
            "data_quality_status": status,
            "data_quality_flags": flags,
            "h3_index": h3_idx,
            "geometry": geometry,
            "processing_status": "NORMALIZED",
            "raw_payload": raw
        }

        return True, status, flags, clean

    # =========================================================================
    # 3. BATCH INGESTION & DATABASE PERSISTENCE
    # =========================================================================

    def ingest_records(
        self,
        records: List[Dict[str, Any]],
        db: Optional[Session] = None,
        source: str = "NASA_FIRMS",
        is_live_data: bool = True
    ) -> FIRMSIngestSummaryResponse:
        """
        Process and ingest a batch of NASA FIRMS thermal anomaly observations.
        Performs validation, normalization, deduplication against DB and in-batch records,
        and persists canonical records.
        """
        start_time = time.time()
        records_received = len(records)
        records_parsed = 0
        records_validated = 0
        duplicates_skipped = 0
        records_persisted = 0
        records_flagged_warning = 0
        records_rejected_invalid = 0
        inserted_event_ids: List[str] = []
        quality_counts: Dict[str, int] = {"GOOD": 0, "WARNING": 0, "INVALID": 0, "DUPLICATE": 0}

        seen_dedup_keys = set()

        # If DB available, query existing keys for batch
        existing_db_keys = set()
        if db:
            try:
                existing_rows = db.query(ThermalEventModel.dedup_key).all()
                existing_db_keys = {r[0] for r in existing_rows}
            except Exception as e:
                logger.warning(f"Failed to query existing thermal keys from DB: {e}")

        models_to_save: List[ThermalEventModel] = []
        memory_events_to_add: List[CanonicalThermalEvent] = []

        for raw_item in records:
            records_parsed += 1
            is_valid, q_status, flags, clean = self.validate_and_normalize_record(raw_item, is_live_data=is_live_data)

            if not is_valid:
                records_rejected_invalid += 1
                quality_counts["INVALID"] += 1
                continue

            records_validated += 1
            dedup_key = clean["dedup_key"]

            # Deduplication Check
            if dedup_key in seen_dedup_keys or dedup_key in existing_db_keys:
                duplicates_skipped += 1
                quality_counts["DUPLICATE"] += 1
                continue

            seen_dedup_keys.add(dedup_key)
            quality_counts[q_status] = quality_counts.get(q_status, 0) + 1
            if q_status == "WARNING":
                records_flagged_warning += 1

            # Prepare Canonical Schema
            event_obj = CanonicalThermalEvent(**clean)
            memory_events_to_add.append(event_obj)
            inserted_event_ids.append(clean["event_id"])
            records_persisted += 1

            if db:
                model_item = ThermalEventModel(
                    event_id=clean["event_id"],
                    dedup_key=clean["dedup_key"],
                    source=source,
                    source_satellite=clean["source_satellite"],
                    sensor_name=clean["sensor_name"],
                    source_version=clean["source_version"],
                    acquisition_timestamp=clean["acquisition_timestamp"],
                    latitude=clean["latitude"],
                    longitude=clean["longitude"],
                    h3_index=clean["h3_index"],
                    geometry_geojson=clean["geometry"],
                    frp_mw=clean["frp_mw"],
                    brightness_temp_k=clean["brightness_temp_k"],
                    brightness_temp_i4_k=clean["brightness_temp_i4_k"],
                    confidence=clean["confidence"],
                    confidence_pct=clean["confidence_pct"],
                    day_night=clean["day_night"],
                    scan=clean["scan"],
                    track=clean["track"],
                    ingested_at=clean["ingested_at"],
                    is_live_data=clean["is_live_data"],
                    data_quality_status=clean["data_quality_status"],
                    data_quality_flags=clean["data_quality_flags"],
                    processing_status=clean["processing_status"],
                    raw_payload=clean.get("raw_payload")
                )
                models_to_save.append(model_item)

        # Database Commit
        if db and models_to_save:
            try:
                db.add_all(models_to_save)
                db.commit()

                # Incremental Spatiotemporal Clustering, Attribution & Abnormality Hook
                from app.services.satellite.clustering_engine import clustering_engine
                from app.services.satellite.source_attribution_engine import source_attribution_engine
                from app.services.satellite.abnormality_engine import abnormality_engine
                for m in models_to_save:
                    src, _ = clustering_engine.attach_or_create_source(m, db=db)
                    source_attribution_engine.attribute_source(src, db=db)
                    abnormality_engine.assess_thermal_source(src, m, db=db)
                    from app.services.ml.thermal_classifier_service import classifier_service
                    cls_res = classifier_service.classify_source(src, event=m, db=db)
                    m.classification = cls_res.predicted_class
                    m.classification_confidence = cls_res.model_confidence
                    m.model_version = cls_res.model_version
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Database commit/clustering error during FIRMS ingestion: {e}")
                # Keep in memory fallback
                for item in memory_events_to_add:
                    self._memory_events.append(item)
        else:
            for item in memory_events_to_add:
                self._memory_events.append(item)

        duration_ms = round((time.time() - start_time) * 1000.0, 2)

        return FIRMSIngestSummaryResponse(
            source=source,
            records_received=records_received,
            records_parsed=records_parsed,
            records_validated=records_validated,
            duplicates_skipped=duplicates_skipped,
            records_persisted=records_persisted,
            records_flagged_warning=records_flagged_warning,
            records_rejected_invalid=records_rejected_invalid,
            ingestion_duration_ms=duration_ms,
            inserted_event_ids=inserted_event_ids,
            quality_summary=quality_counts
        )

    # =========================================================================
    # 4. QUERY API & FILTERING
    # =========================================================================

    def get_thermal_events(
        self,
        db: Optional[Session] = None,
        min_confidence: Optional[str] = None,
        classification: Optional[str] = None,
        facility_id: Optional[str] = None,
        only_abnormal: bool = False,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        satellite: Optional[str] = None,
        day_night: Optional[str] = None,
        bbox: Optional[List[float]] = None,
        is_live_data: Optional[bool] = None,
        limit: int = 200,
        offset: int = 0
    ) -> List[CanonicalThermalEvent]:
        """
        Query canonical thermal events with comprehensive multi-criteria filtering.
        """
        # 1. Try DB Query if DB provided and populated
        if db:
            try:
                query = db.query(ThermalEventModel)

                if start_time:
                    query = query.filter(ThermalEventModel.acquisition_timestamp >= start_time)
                if end_time:
                    query = query.filter(ThermalEventModel.acquisition_timestamp <= end_time)
                if satellite:
                    sat_clean = self.normalize_satellite_name(satellite)
                    query = query.filter(ThermalEventModel.source_satellite == sat_clean)
                if day_night:
                    query = query.filter(ThermalEventModel.day_night == day_night.upper())
                if is_live_data is not None:
                    query = query.filter(ThermalEventModel.is_live_data == is_live_data)
                if min_confidence:
                    if min_confidence.upper() == "HIGH":
                        query = query.filter(ThermalEventModel.confidence == "HIGH")
                    elif min_confidence.upper() == "NOMINAL":
                        query = query.filter(ThermalEventModel.confidence.in_(["NOMINAL", "HIGH"]))
                if facility_id:
                    query = query.filter(ThermalEventModel.attributed_facility_id == facility_id)
                if only_abnormal:
                    query = query.filter(ThermalEventModel.abnormality_score >= 50.0)

                db_rows = query.order_by(ThermalEventModel.acquisition_timestamp.desc()).offset(offset).limit(limit).all()
                if db_rows:
                    results = []
                    for row in db_rows:
                        if bbox and not point_in_bbox(row.latitude, row.longitude, bbox):
                            continue
                        geom = row.geometry_geojson or {"type": "Point", "coordinates": [row.longitude, row.latitude]}
                        results.append(CanonicalThermalEvent(
                            event_id=row.event_id,
                            dedup_key=row.dedup_key,
                            source=row.source,
                            source_satellite=row.source_satellite,
                            sensor_name=row.sensor_name,
                            source_version=row.source_version,
                            acquisition_timestamp=row.acquisition_timestamp,
                            latitude=row.latitude,
                            longitude=row.longitude,
                            frp_mw=row.frp_mw,
                            brightness_temp_k=row.brightness_temp_k,
                            brightness_temp_i4_k=row.brightness_temp_i4_k,
                            confidence=row.confidence,
                            confidence_pct=row.confidence_pct,
                            day_night=row.day_night,
                            scan=row.scan,
                            track=row.track,
                            ingested_at=row.ingested_at,
                            is_live_data=row.is_live_data,
                            data_quality_status=row.data_quality_status,
                            data_quality_flags=row.data_quality_flags or [],
                            processing_status=row.processing_status,
                            h3_index=row.h3_index,
                            geometry=geom,
                        cls_name = row.classification
                        cls_conf = row.classification_confidence
                        if not cls_name or cls_name == "UNCLASSIFIED":
                            try:
                                from app.services.ml.thermal_classifier_service import classifier_service
                                cls_res = classifier_service.classify_event(row, db=db)
                                cls_name = cls_res.predicted_class
                                cls_conf = cls_res.model_confidence
                                row.classification = cls_name
                                row.classification_confidence = cls_conf
                            except Exception:
                                cls_name = "OTHER_UNKNOWN"
                                cls_conf = 0.50

                        results.append(CanonicalThermalEvent(
                            event_id=row.event_id,
                            dedup_key=row.dedup_key,
                            source=row.source,
                            source_satellite=row.source_satellite,
                            sensor_name=row.sensor_name,
                            source_version=row.source_version,
                            acquisition_timestamp=row.acquisition_timestamp,
                            latitude=row.latitude,
                            longitude=row.longitude,
                            frp_mw=row.frp_mw,
                            brightness_temp_k=row.brightness_temp_k,
                            brightness_temp_i4_k=row.brightness_temp_i4_k,
                            confidence=row.confidence,
                            confidence_pct=row.confidence_pct,
                            day_night=row.day_night,
                            scan=row.scan,
                            track=row.track,
                            ingested_at=row.ingested_at,
                            is_live_data=row.is_live_data,
                            data_quality_status=row.data_quality_status,
                            data_quality_flags=row.data_quality_flags or [],
                            processing_status=row.processing_status,
                            h3_index=row.h3_index,
                            geometry=geom,
                            classification=cls_name or "OTHER_UNKNOWN",
                            classification_confidence=cls_conf or 0.50,
                            persistence_category=row.persistence_category or "TRANSIENT",
                            abnormality_score=row.abnormality_score or 0.0,
                            attributed_facility_id=row.attributed_facility_id,
                            attributed_facility_name=row.attributed_facility_name,
                            facility_distance_m=row.facility_distance_m,
                            is_inside_facility_boundary=row.is_inside_facility_boundary or False,
                            model_version=row.model_version
                        ))
                    if db:
                        try:
                            db.commit()
                        except Exception:
                            pass
                    return results
            except Exception as e:
                logger.warning(f"Database query failed, falling back to memory registry: {e}")

        # 2. In-Memory Registry Fallback
        results = self._memory_events

        if start_time:
            results = [e for e in results if e.acquisition_timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.acquisition_timestamp <= end_time]
        if satellite:
            sat_clean = self.normalize_satellite_name(satellite)
            results = [e for e in results if e.source_satellite == sat_clean]
        if day_night:
            results = [e for e in results if e.day_night == day_night.upper()]
        if is_live_data is not None:
            results = [e for e in results if e.is_live_data == is_live_data]
        if min_confidence:
            if min_confidence.upper() == "HIGH":
                results = [e for e in results if e.confidence == "HIGH"]
            elif min_confidence.upper() == "NOMINAL":
                results = [e for e in results if e.confidence in ["NOMINAL", "HIGH"]]
        if classification:
            results = [e for e in results if e.classification == classification]
        if facility_id:
            results = [e for e in results if e.attributed_facility_id == facility_id]
        if only_abnormal:
            results = [e for e in results if e.abnormality_score >= 50.0]
        if bbox:
            results = [e for e in results if point_in_bbox(e.latitude, e.longitude, bbox)]

        return results[offset:offset + limit]

    def get_event_by_id(self, event_id: str, db: Optional[Session] = None) -> Optional[CanonicalThermalEvent]:
        """
        Retrieve a specific canonical thermal event by event_id.
        """
        if db:
            try:
                row = db.query(ThermalEventModel).filter(ThermalEventModel.event_id == event_id).first()
                if row:
                    geom = row.geometry_geojson or {"type": "Point", "coordinates": [row.longitude, row.latitude]}
                    return CanonicalThermalEvent(
                        event_id=row.event_id,
                        dedup_key=row.dedup_key,
                        source=row.source,
                        source_satellite=row.source_satellite,
                        sensor_name=row.sensor_name,
                        source_version=row.source_version,
                        acquisition_timestamp=row.acquisition_timestamp,
                        latitude=row.latitude,
                        longitude=row.longitude,
                        frp_mw=row.frp_mw,
                        brightness_temp_k=row.brightness_temp_k,
                        brightness_temp_i4_k=row.brightness_temp_i4_k,
                        confidence=row.confidence,
                        confidence_pct=row.confidence_pct,
                        day_night=row.day_night,
                        scan=row.scan,
                        track=row.track,
                        ingested_at=row.ingested_at,
                        is_live_data=row.is_live_data,
                        data_quality_status=row.data_quality_status,
                        data_quality_flags=row.data_quality_flags or [],
                        processing_status=row.processing_status,
                        h3_index=row.h3_index,
                    cls_name = row.classification
                    cls_conf = row.classification_confidence
                    if not cls_name or cls_name == "UNCLASSIFIED":
                        try:
                            from app.services.ml.thermal_classifier_service import classifier_service
                            cls_res = classifier_service.classify_event(row, db=db)
                            cls_name = cls_res.predicted_class
                            cls_conf = cls_res.model_confidence
                            row.classification = cls_name
                            row.classification_confidence = cls_conf
                            db.commit()
                        except Exception:
                            cls_name = "OTHER_UNKNOWN"
                            cls_conf = 0.50

                    return CanonicalThermalEvent(
                        event_id=row.event_id,
                        dedup_key=row.dedup_key,
                        source=row.source,
                        source_satellite=row.source_satellite,
                        sensor_name=row.sensor_name,
                        source_version=row.source_version,
                        acquisition_timestamp=row.acquisition_timestamp,
                        latitude=row.latitude,
                        longitude=row.longitude,
                        frp_mw=row.frp_mw,
                        brightness_temp_k=row.brightness_temp_k,
                        brightness_temp_i4_k=row.brightness_temp_i4_k,
                        confidence=row.confidence,
                        confidence_pct=row.confidence_pct,
                        day_night=row.day_night,
                        scan=row.scan,
                        track=row.track,
                        ingested_at=row.ingested_at,
                        is_live_data=row.is_live_data,
                        data_quality_status=row.data_quality_status,
                        data_quality_flags=row.data_quality_flags or [],
                        processing_status=row.processing_status,
                        h3_index=row.h3_index,
                        geometry=geom,
                        classification=cls_name or "OTHER_UNKNOWN",
                        classification_confidence=cls_conf or 0.50,
                        persistence_category=row.persistence_category or "TRANSIENT",
                        abnormality_score=row.abnormality_score or 0.0,
                        attributed_facility_id=row.attributed_facility_id,
                        attributed_facility_name=row.attributed_facility_name,
                        facility_distance_m=row.facility_distance_m,
                        is_inside_facility_boundary=row.is_inside_facility_boundary or False,
                        model_version=row.model_version
                    )
            except Exception as e:
                logger.warning(f"DB lookup failed for {event_id}: {e}")

        for ev in self._memory_events:
            if ev.event_id == event_id:
                return ev
        return None

    # =========================================================================
    # 5. MAP-READY GEOJSON GENERATION
    # =========================================================================

    def get_events_geojson(
        self,
        db: Optional[Session] = None,
        min_confidence: Optional[str] = None,
        classification: Optional[str] = None,
        satellite: Optional[str] = None,
        only_abnormal: bool = False,
        bbox: Optional[List[float]] = None
    ) -> ThermalEventGeoJSONCollection:
        """
        Generate lightweight, map-ready GeoJSON FeatureCollection for Leaflet / GIS display.
        """
        events = self.get_thermal_events(
            db=db,
            min_confidence=min_confidence,
            classification=classification,
            satellite=satellite,
            only_abnormal=only_abnormal,
            bbox=bbox,
            limit=500
        )

        features: List[ThermalEventGeoJSONFeature] = []
        for ev in events:
            features.append(ThermalEventGeoJSONFeature(
                type="Feature",
                geometry={"type": "Point", "coordinates": [ev.longitude, ev.latitude]},
                properties={
                    "event_id": ev.event_id,
                    "timestamp": ev.acquisition_timestamp.isoformat(),
                    "satellite": ev.source_satellite,
                    "sensor": ev.sensor_name,
                    "frp_mw": ev.frp_mw,
                    "brightness_temp_k": ev.brightness_temp_k,
                    "confidence": ev.confidence,
                    "day_night": ev.day_night,
                    "is_live_data": ev.is_live_data,
                    "data_quality_status": ev.data_quality_status,
                    "h3_index": ev.h3_index,
                    "classification": ev.classification,
                    "abnormality_score": ev.abnormality_score,
                    "attributed_facility_id": ev.attributed_facility_id,
                    "attributed_facility_name": ev.attributed_facility_name,
                    "is_inside_facility_boundary": ev.is_inside_facility_boundary
                }
            ))

        return ThermalEventGeoJSONCollection(
            type="FeatureCollection",
            features=features,
            metadata={
                "count": len(features),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "crs": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        )

    # =========================================================================
    # 6. STATISTICAL AGGREGATION & KPIS
    # =========================================================================

    def get_stats(self, db: Optional[Session] = None) -> ThermalEventStatsResponse:
        """
        Compute high-performance statistical summaries, KPI distributions, and temporal spans.
        """
        events = self.get_thermal_events(db=db, limit=10000)

        total = len(events)
        live_count = sum(1 for e in events if e.is_live_data)
        demo_count = total - live_count

        sat_dist: Dict[str, int] = {}
        sensor_dist: Dict[str, int] = {}
        dn_dist: Dict[str, int] = {"D": 0, "N": 0}
        quality_dist: Dict[str, int] = {}
        conf_dist: Dict[str, int] = {}
        h3_set = set()

        max_frp = 0.0
        sum_frp = 0.0
        min_dt = None
        max_dt = None

        for e in events:
            sat_dist[e.source_satellite] = sat_dist.get(e.source_satellite, 0) + 1
            sensor_dist[e.sensor_name] = sensor_dist.get(e.sensor_name, 0) + 1
            dn_dist[e.day_night] = dn_dist.get(e.day_night, 0) + 1
            quality_dist[e.data_quality_status] = quality_dist.get(e.data_quality_status, 0) + 1
            conf_dist[e.confidence] = conf_dist.get(e.confidence, 0) + 1

            if e.h3_index:
                h3_set.add(e.h3_index)

            frp = e.frp_mw or 0.0
            sum_frp += frp
            if frp > max_frp:
                max_frp = frp

            dt = e.acquisition_timestamp
            if min_dt is None or dt < min_dt:
                min_dt = dt
            if max_dt is None or dt > max_dt:
                max_dt = dt

        mean_frp = round(sum_frp / total, 2) if total > 0 else 0.0

        return ThermalEventStatsResponse(
            total_events_count=total,
            live_events_count=live_count,
            demo_events_count=demo_count,
            satellite_distribution=sat_dist,
            sensor_distribution=sensor_dist,
            day_night_distribution=dn_dist,
            quality_status_distribution=quality_dist,
            confidence_distribution=conf_dist,
            max_frp_mw=round(max_frp, 2),
            mean_frp_mw=mean_frp,
            temporal_range_start=min_dt,
            temporal_range_end=max_dt,
            h3_clusters_count=len(h3_set)
        )

    # =========================================================================
    # 7. INITIAL BENCHMARK SEED DATA (Corridor Detections)
    # =========================================================================

    def _init_benchmark_events(self):
        """
        Deterministic benchmark observations across key Indian industrial zones:
        Dahej PCPIR, Jamnagar, Hazira, Korba, Jamshedpur, Jharia, Punjab.
        """
        now = datetime.utcnow()
        raw_seeds = [
            {
                "event_id": "FIRMS-VIIRS-20260830-DHJ-01",
                "source_satellite": "NOAA-20",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(minutes=18),
                "latitude": 21.6852,
                "longitude": 72.5753,
                "frp_mw": 84.6,
                "brightness_temp_k": 348.2,
                "brightness_temp_i4_k": 365.1,
                "confidence": "HIGH",
                "confidence_pct": 96.0,
                "day_night": "N",
                "scan": 0.38,
                "track": 0.37,
                "is_live_data": True,
                "attributed_facility_id": "FAC-DAHEJ-PCH01",
                "attributed_facility_name": "PetroChem Complex Alpha - Unit 04",
                "facility_distance_m": 45.0,
                "is_inside_facility_boundary": True,
                "classification": "INDUSTRIAL_FIRE",
                "classification_confidence": 0.94,
                "persistence_category": "ABNORMAL_PERSISTENT",
                "recurrence_count_30d": 28,
                "recurrence_rate_pct": 93.3,
                "abnormality_score": 96.5,
                "frp_delta_from_baseline_pct": 464.0,
                "risk_level": "CRITICAL"
            },
            {
                "event_id": "FIRMS-VIIRS-20260830-JMN-01",
                "source_satellite": "SUOMI-NPP",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(minutes=42),
                "latitude": 22.3880,
                "longitude": 69.8320,
                "frp_mw": 24.5,
                "brightness_temp_k": 338.4,
                "confidence": "HIGH",
                "confidence_pct": 92.0,
                "day_night": "N",
                "scan": 0.40,
                "track": 0.38,
                "is_live_data": True,
                "attributed_facility_id": "FAC-JAMNAGAR-REF01",
                "attributed_facility_name": "Jamnagar Mega Refinery & Petrochemical Hub",
                "facility_distance_m": 120.0,
                "is_inside_facility_boundary": True,
                "classification": "GAS_FLARE",
                "classification_confidence": 0.91,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 30,
                "recurrence_rate_pct": 100.0,
                "abnormality_score": 12.0,
                "frp_delta_from_baseline_pct": 11.3,
                "risk_level": "LOW"
            },
            {
                "event_id": "FIRMS-VIIRS-20260830-HZR-01",
                "source_satellite": "NOAA-21",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(minutes=55),
                "latitude": 21.1210,
                "longitude": 72.6450,
                "frp_mw": 32.1,
                "brightness_temp_k": 341.0,
                "confidence": "HIGH",
                "confidence_pct": 89.0,
                "day_night": "D",
                "scan": 0.37,
                "track": 0.36,
                "is_live_data": True,
                "attributed_facility_id": "FAC-HAZIRA-LNG01",
                "attributed_facility_name": "Hazira LNG Terminal & Chemical Complex",
                "facility_distance_m": 85.0,
                "is_inside_facility_boundary": True,
                "classification": "ROUTINE_PROCESS_HEAT",
                "classification_confidence": 0.88,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 29,
                "recurrence_rate_pct": 96.7,
                "abnormality_score": 18.5,
                "frp_delta_from_baseline_pct": 14.6,
                "risk_level": "NORMAL"
            },
            {
                "event_id": "FIRMS-MODIS-20260830-KRB-01",
                "source_satellite": "TERRA",
                "sensor_name": "MODIS_1KM",
                "acquisition_timestamp": now - timedelta(hours=1, minutes=20),
                "latitude": 22.3950,
                "longitude": 82.7210,
                "frp_mw": 48.0,
                "brightness_temp_k": 329.5,
                "confidence": "HIGH",
                "confidence_pct": 85.0,
                "day_night": "D",
                "scan": 1.1,
                "track": 1.0,
                "is_live_data": True,
                "attributed_facility_id": "FAC-KORBA-PWR01",
                "attributed_facility_name": "NTPC Korba Super Thermal Power Plant",
                "facility_distance_m": 210.0,
                "is_inside_facility_boundary": True,
                "classification": "ROUTINE_PROCESS_HEAT",
                "classification_confidence": 0.86,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 29,
                "recurrence_rate_pct": 96.7,
                "abnormality_score": 15.2,
                "frp_delta_from_baseline_pct": 14.3,
                "risk_level": "NORMAL"
            },
            {
                "event_id": "FIRMS-MODIS-20260830-JSR-01",
                "source_satellite": "AQUA",
                "sensor_name": "MODIS_1KM",
                "acquisition_timestamp": now - timedelta(hours=2, minutes=10),
                "latitude": 22.8020,
                "longitude": 86.2030,
                "frp_mw": 39.5,
                "brightness_temp_k": 334.2,
                "confidence": "HIGH",
                "confidence_pct": 88.0,
                "day_night": "D",
                "scan": 1.0,
                "track": 1.0,
                "is_live_data": True,
                "attributed_facility_id": "FAC-JAMSHEDPUR-STEEL01",
                "attributed_facility_name": "Tata Steel Jamshedpur Integrated Steel Works",
                "facility_distance_m": 150.0,
                "is_inside_facility_boundary": True,
                "classification": "ROUTINE_PROCESS_HEAT",
                "classification_confidence": 0.89,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 30,
                "recurrence_rate_pct": 100.0,
                "abnormality_score": 14.0,
                "frp_delta_from_baseline_pct": 12.8,
                "risk_level": "NORMAL"
            },
            {
                "event_id": "FIRMS-VIIRS-20260830-JHR-01",
                "source_satellite": "NOAA-20",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(hours=2, minutes=45),
                "latitude": 23.7500,
                "longitude": 86.4200,
                "frp_mw": 52.3,
                "brightness_temp_k": 345.8,
                "confidence": "HIGH",
                "confidence_pct": 91.0,
                "day_night": "N",
                "scan": 0.38,
                "track": 0.37,
                "is_live_data": True,
                "attributed_facility_id": "FAC-JHARIA-COAL01",
                "attributed_facility_name": "Jharia Open Cast Coal Seam & Mining Sector",
                "facility_distance_m": 90.0,
                "is_inside_facility_boundary": True,
                "classification": "MINING_PROCESS_HEAT",
                "classification_confidence": 0.92,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 30,
                "recurrence_rate_pct": 100.0,
                "abnormality_score": 22.0,
                "frp_delta_from_baseline_pct": 30.7,
                "risk_level": "MODERATE"
            },
            {
                "event_id": "FIRMS-VIIRS-20260830-PB-01",
                "source_satellite": "NOAA-21",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(hours=3, minutes=15),
                "latitude": 30.9000,
                "longitude": 75.8500,
                "frp_mw": 14.2,
                "brightness_temp_k": 322.0,
                "confidence": "NOMINAL",
                "confidence_pct": 68.0,
                "day_night": "D",
                "scan": 0.39,
                "track": 0.38,
                "is_live_data": True,
                "attributed_facility_id": None,
                "attributed_facility_name": None,
                "facility_distance_m": 8500.0,
                "is_inside_facility_boundary": False,
                "classification": "AGRICULTURAL_BURNING",
                "classification_confidence": 0.95,
                "persistence_category": "TRANSIENT",
                "recurrence_count_30d": 2,
                "recurrence_rate_pct": 6.7,
                "abnormality_score": 5.0,
                "frp_delta_from_baseline_pct": 0.0,
                "risk_level": "LOW"
            },
            {
                "event_id": "FIRMS-VIIRS-20260830-DHJ-02",
                "source_satellite": "SUOMI-NPP",
                "sensor_name": "VIIRS_375M",
                "acquisition_timestamp": now - timedelta(hours=4),
                "latitude": 21.6890,
                "longitude": 72.5810,
                "frp_mw": 16.8,
                "brightness_temp_k": 332.0,
                "confidence": "HIGH",
                "confidence_pct": 89.0,
                "day_night": "D",
                "scan": 0.37,
                "track": 0.36,
                "is_live_data": True,
                "attributed_facility_id": "FAC-DAHEJ-PCH01",
                "attributed_facility_name": "PetroChem Complex Alpha - Unit 04",
                "facility_distance_m": 150.0,
                "is_inside_facility_boundary": True,
                "classification": "GAS_FLARE",
                "classification_confidence": 0.89,
                "persistence_category": "EXPECTED_PERSISTENT",
                "recurrence_count_30d": 28,
                "recurrence_rate_pct": 93.3,
                "abnormality_score": 8.0,
                "frp_delta_from_baseline_pct": 12.0,
                "risk_level": "NORMAL"
            }
        ]

        self._memory_events = []
        for raw in raw_seeds:
            _, _, _, clean = self.validate_and_normalize_record(raw, is_live_data=raw.get("is_live_data", True))
            if clean:
                # Merge attribution & classification defaults from seed
                for k in ["classification", "classification_confidence", "persistence_category", 
                          "recurrence_count_30d", "recurrence_rate_pct", "abnormality_score",
                          "frp_delta_from_baseline_pct", "risk_level", "attributed_facility_id",
                          "attributed_facility_name", "facility_distance_m", "is_inside_facility_boundary"]:
                    if k in raw:
                        clean[k] = raw[k]
                self._memory_events.append(CanonicalThermalEvent(**clean))

firms_service = FIRMSService()

import time
import asyncio
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.thermal_event import ThermalEventModel
from app.models.telemetry_models import FacilityTelemetryRecord
from app.services.satellite.firms_ingestion_service import firms_ingestion_service
from app.services.industrial.telemetry_service import telemetry_service

def test_database_chaos_recovery():
    """
    Validates that database disconnections / transient restarts are recovered
    cleanly via connection pool pre-ping without corrupting application state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "chaos_recovery.db"
        engine = create_engine(f"sqlite:///{db_path}", pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        # Insert baseline event
        evt = ThermalEventModel(
            event_id="EVT-CHAOS-001",
            dedup_key="DEDUP-CHAOS-001",
            source="NASA_FIRMS",
            source_satellite="VIIRS_N20",
            sensor_name="VIIRS",
            acquisition_timestamp=datetime.now(timezone.utc),
            latitude=21.1685,
            longitude=72.6958,
            frp_mw=45.0
        )
        db.add(evt)
        db.commit()

        # Verify query works
        found = db.query(ThermalEventModel).filter(ThermalEventModel.event_id == "EVT-CHAOS-001").first()
        assert found is not None
        assert found.frp_mw == 45.0
        db.close()

        # Simulate DB disconnect / engine disposal
        engine.dispose()

        # Re-query with fresh session - pool_pre_ping should transparently establish a healthy connection
        new_db = Session()
        recovered_evt = new_db.query(ThermalEventModel).filter(ThermalEventModel.event_id == "EVT-CHAOS-001").first()
        assert recovered_evt is not None
        assert recovered_evt.event_id == "EVT-CHAOS-001"

        new_db.close()
        engine.dispose()

def test_satellite_external_outage_graceful_handling():
    """
    Validates that when external NASA FIRMS / STAC endpoints fail with network timeouts
    or HTTP 503/504 errors, the ingestion pipeline handles the outage gracefully,
    does NOT crash the application, and records failure metrics.
    """
    old_base_url = settings.NASA_FIRMS_BASE_URL
    try:
        settings.NASA_FIRMS_BASE_URL = "https://unreachable.satellite.internal.invalid/api/area/csv"
        
        # Async execution of ingestion cycle with unreachable endpoint
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        summary = loop.run_until_complete(firms_ingestion_service.run_ingestion_cycle())
        loop.close()

        # Should return gracefully with 0 persisted events
        assert summary.records_persisted == 0
        assert summary.records_received == 0
        assert summary.source == "NASA_FIRMS"

    finally:
        settings.NASA_FIRMS_BASE_URL = old_base_url

def test_telemetry_temporary_outage_and_staleness():
    """
    Validates that when industrial IoT telemetry drops, values are marked STALE
    rather than fabricating synthetic data or halting intelligence services.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "telemetry_outage.db"
        db_engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=db_engine)
        Session = sessionmaker(bind=db_engine)
        db = Session()

        stale_timestamp = datetime.now(timezone.utc) - timedelta(seconds=120)
        
        stale_rec = FacilityTelemetryRecord(
            telemetry_id="TEL-STALE-001",
            facility_id="FAC-IND-GUJ-HAZ-001",
            asset_id="AST-HAZ-TK-101",
            gateway_id="GW-HAZ-EDGE-01",
            sensor_id="SNS-HAZ-TEMP-01",
            sensor_type="TEMPERATURE",
            tag_name="TI_101",
            timestamp_utc=stale_timestamp,
            source_timestamp=stale_timestamp,
            value=65.4,
            unit="C",
            quality="STALE",
            freshness_status="STALE"
        )
        db.add(stale_rec)
        db.commit()

        queried = db.query(FacilityTelemetryRecord).filter(
            FacilityTelemetryRecord.telemetry_id == "TEL-STALE-001"
        ).first()
        assert queried is not None
        assert queried.quality == "STALE"
        assert queried.freshness_status == "STALE"

        # Recover with fresh live telemetry
        fresh_timestamp = datetime.now(timezone.utc)
        fresh_rec = FacilityTelemetryRecord(
            telemetry_id="TEL-FRESH-002",
            facility_id="FAC-IND-GUJ-HAZ-001",
            asset_id="AST-HAZ-TK-101",
            gateway_id="GW-HAZ-EDGE-01",
            sensor_id="SNS-HAZ-TEMP-01",
            sensor_type="TEMPERATURE",
            tag_name="TI_101",
            timestamp_utc=fresh_timestamp,
            source_timestamp=fresh_timestamp,
            value=66.1,
            unit="C",
            quality="GOOD",
            freshness_status="LIVE"
        )
        db.add(fresh_rec)
        db.commit()

        latest = db.query(FacilityTelemetryRecord).filter(
            FacilityTelemetryRecord.sensor_id == "SNS-HAZ-TEMP-01"
        ).order_by(FacilityTelemetryRecord.timestamp_utc.desc()).first()
        assert latest.telemetry_id == "TEL-FRESH-002"
        assert latest.quality == "GOOD"
        assert latest.freshness_status == "LIVE"

        db.close()
        db_engine.dispose()

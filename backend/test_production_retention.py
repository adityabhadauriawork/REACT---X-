import os
import sys
import tempfile
import gzip
import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base
from app.models.thermal_event import ThermalEventModel
from app.models.telemetry_models import FacilityTelemetryRecord
from app.models.audit import DecisionAuditModel

from scripts.archive_retention import archive_and_purge_thermal_events, archive_and_purge_telemetry

def test_retention_preserves_fires_and_archives_old_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_retention.db"
        archive_dir = tmp_path / "archives"

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        now = datetime.now(timezone.utc)
        old_time = now - timedelta(days=120)
        recent_time = now - timedelta(days=10)

        # 1. Old normal detection (SHOULD be archived)
        db.add(ThermalEventModel(
            event_id="EVT-OLD-001",
            dedup_key="DEDUP-OLD-001",
            source="NASA_FIRMS",
            source_satellite="VIIRS_N20",
            sensor_name="VIIRS",
            acquisition_timestamp=old_time,
            latitude=21.1,
            longitude=72.7,
            frp_mw=15.0,
            classification="Flare Stack"
        ))

        # 2. Old Industrial Fire event (MUST BE PRESERVED - never deleted)
        db.add(ThermalEventModel(
            event_id="EVT-OLD-FIRE",
            dedup_key="DEDUP-OLD-FIRE",
            source="NASA_FIRMS",
            source_satellite="VIIRS_N20",
            sensor_name="VIIRS",
            acquisition_timestamp=old_time,
            latitude=21.1,
            longitude=72.7,
            frp_mw=150.0,
            classification="Industrial Fire"
        ))

        # 3. Recent detection (MUST BE PRESERVED)
        db.add(ThermalEventModel(
            event_id="EVT-RECENT-001",
            dedup_key="DEDUP-RECENT-001",
            source="NASA_FIRMS",
            source_satellite="VIIRS_N20",
            sensor_name="VIIRS",
            acquisition_timestamp=recent_time,
            latitude=21.1,
            longitude=72.7,
            frp_mw=20.0,
            classification="Flare Stack"
        ))

        # 4. Old telemetry (GOOD -> archived)
        db.add(FacilityTelemetryRecord(
            telemetry_id="TEL-OLD-001",
            facility_id="FAC-001",
            asset_id="AST-001",
            gateway_id="GW-001",
            sensor_id="SNS-001",
            sensor_type="TEMPERATURE",
            tag_name="TIC-101",
            timestamp_utc=old_time,
            source_timestamp=old_time,
            value=85.2,
            unit="C",
            quality="GOOD"
        ))

        # 5. Old warning telemetry (BAD/ALARM -> PRESERVED for audit trail)
        db.add(FacilityTelemetryRecord(
            telemetry_id="TEL-OLD-ALARM",
            facility_id="FAC-001",
            asset_id="AST-001",
            gateway_id="GW-001",
            sensor_id="SNS-001",
            sensor_type="TEMPERATURE",
            tag_name="TIC-101",
            timestamp_utc=old_time,
            source_timestamp=old_time,
            value=250.0,
            unit="C",
            quality="CRITICAL"
        ))

        db.commit()

        # Run archival for 90 days cutoff
        cutoff = now - timedelta(days=90)
        res_thermal = archive_and_purge_thermal_events(db, cutoff, archive_dir, dry_run=False)
        res_telemetry = archive_and_purge_telemetry(db, cutoff, archive_dir, dry_run=False)

        assert res_thermal["events_archived"] == 1
        assert res_thermal["archive_file"] is not None
        assert Path(res_thermal["archive_file"]).exists()

        assert res_telemetry["telemetry_archived"] == 1
        assert res_telemetry["archive_file"] is not None
        assert Path(res_telemetry["archive_file"]).exists()

        # Check DB contents: EVT-OLD-001 deleted, EVT-OLD-FIRE and EVT-RECENT-001 preserved
        remaining_thermal = db.query(ThermalEventModel).all()
        remaining_thermal_ids = {r.event_id for r in remaining_thermal}
        assert remaining_thermal_ids == {"EVT-OLD-FIRE", "EVT-RECENT-001"}

        # Check Telemetry: TEL-OLD-001 deleted, TEL-OLD-ALARM preserved
        remaining_telemetry = db.query(FacilityTelemetryRecord).all()
        remaining_tel_ids = {t.telemetry_id for t in remaining_telemetry}
        assert remaining_tel_ids == {"TEL-OLD-ALARM"}

        db.close()
        engine.dispose()


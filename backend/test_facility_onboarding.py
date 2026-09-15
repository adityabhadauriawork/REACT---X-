import os
import sys
import json
import pytest
from pathlib import Path

# Add backend and project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.models.facility import IndustrialFacilityModel
from app.models.plant import PlantModel, AssetModel
from app.models.telemetry_models import SensorMetadataModel
from app.models.audit import DecisionAuditModel
from scripts.onboard_facility import onboard_facility, validate_facility_config

def test_facility_onboarding_paradip():
    """Verifies that a new Indian facility (IOCL Paradip) is onboarded declaratively."""
    config_path = Path(__file__).resolve().parent.parent / "data" / "onboarding_sample_paradip.json"
    assert config_path.exists(), "Sample onboarding configuration must exist"

    # 1. Test validation logic
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    errors = validate_facility_config(config)
    assert len(errors) == 0, f"Validation errors found: {errors}"

    # 2. Test dry-run
    dry_res = onboard_facility(config_path, dry_run=True)
    assert dry_res["status"] == "validated_dry_run"
    assert dry_res["facility_id"] == "FAC-IND-ODI-PAR-002"
    assert dry_res["assets_count"] == 3
    assert dry_res["sensors_count"] == 3

    # 3. Test actual live onboarding
    result = onboard_facility(config_path, dry_run=False)
    assert result["status"] == "success"
    assert result["facility_id"] == "FAC-IND-ODI-PAR-002"
    assert result["state"] == "Odisha"

    # 4. Verify DB records
    db = SessionLocal()
    try:
        # Spatial Facility
        fac = db.query(IndustrialFacilityModel).filter(
            IndustrialFacilityModel.facility_id == "FAC-IND-ODI-PAR-002"
        ).first()
        assert fac is not None
        assert "Paradip" in fac.name
        assert fac.state == "Odisha"
        assert fac.latitude == 20.2854
        assert fac.longitude == 86.6432

        # Plant Site
        plant = db.query(PlantModel).filter(PlantModel.id == "FAC-IND-ODI-PAR-002").first()
        assert plant is not None
        assert plant.name == "Indian Oil Paradip Refinery & Petrochemical Complex"

        # Assets
        assets = db.query(AssetModel).filter(
            AssetModel.id.in_(["AST-PAR-AVU-COL-01", "AST-PAR-FCC-REG-01", "AST-PAR-TK-501"])
        ).all()
        assert len(assets) == 3
        asset_names = {a.name for a in assets}
        assert "Crude Atmospheric Distillation Column C-101" in asset_names


        # Sensors
        sensors = db.query(SensorMetadataModel).filter(
            SensorMetadataModel.facility_id == "FAC-IND-ODI-PAR-002"
        ).all()
        assert len(sensors) == 3

        # Audit log
        audit = db.query(DecisionAuditModel).filter(
            DecisionAuditModel.incident_id == "FACILITY-ONBOARDING"
        ).order_by(DecisionAuditModel.timestamp.desc()).first()
        assert audit is not None
        assert "FAC-IND-ODI-PAR-002" in audit.input_summary
    finally:
        db.close()

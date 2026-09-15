#!/usr/bin/env python3
"""
REACT-X Production Facility Onboarding Utility
==============================================
Enables zero-code-modification declarative onboarding of any Indian industrial facility,
refinery, chemical complex, or power plant into the REACT-X command platform.

Usage:
    python scripts/onboard_facility.py --config <path_to_facility_json> [--dry-run]
"""

import os
import sys
import json
import uuid
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.core.database import SessionLocal, engine, Base
from app.models.facility import IndustrialFacilityModel
from app.models.plant import PlantModel, AssetModel
from app.models.telemetry_models import SensorMetadataModel
from app.models.audit import DecisionAuditModel

REQUIRED_FIELDS = [
    "facility_id", "name", "operator_name", "facility_type",
    "state", "district", "center_lat", "center_lon", "fence_radius_m"
]

def validate_facility_config(config: dict) -> list:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"Missing mandatory field: '{field}'")
    
    # Validate coordinates
    lat = config.get("center_lat")
    lon = config.get("center_lon")
    if lat is not None and not (-90 <= lat <= 90):
        errors.append(f"Invalid latitude: {lat}")
    if lon is not None and not (-180 <= lon <= 180):
        errors.append(f"Invalid longitude: {lon}")
        
    return errors

def onboard_facility(config_path: Path, dry_run: bool = False) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    errors = validate_facility_config(config)
    if errors:
        raise ValueError("Facility validation failed:\n- " + "\n- ".join(errors))

    if dry_run:
        return {
            "status": "validated_dry_run",
            "facility_id": config["facility_id"],
            "name": config["name"],
            "assets_count": len(config.get("assets", [])),
            "sensors_count": len(config.get("sensors", [])),
            "cameras_count": len(config.get("cameras", []))
        }

    db = SessionLocal()
    try:
        facility_id = config["facility_id"]

        # 1. Register in Authoritative Spatial Industrial Registry
        existing_fac = db.query(IndustrialFacilityModel).filter(
            IndustrialFacilityModel.facility_id == facility_id
        ).first()

        if existing_fac:
            existing_fac.name = config["name"]
            existing_fac.operator_name = config.get("operator_name")
            existing_fac.facility_type = config.get("facility_type", "PETROCHEMICAL")
            existing_fac.subtype = config.get("subtype")
            existing_fac.latitude = config["center_lat"]
            existing_fac.longitude = config["center_lon"]
            existing_fac.state = config["state"]
            existing_fac.district = config["district"]
            existing_fac.fence_radius_m = config.get("fence_radius_m", 1500.0)
            existing_fac.boundary_geojson = config.get("boundary_geojson")
        else:
            new_fac = IndustrialFacilityModel(
                facility_id=facility_id,
                source="AUTHORITATIVE_ONBOARDING",
                source_id=f"REG-{uuid.uuid4().hex[:8]}",
                name=config["name"],
                operator_name=config.get("operator_name"),
                facility_type=config.get("facility_type", "PETROCHEMICAL"),
                subtype=config.get("subtype"),
                latitude=config["center_lat"],
                longitude=config["center_lon"],
                state=config["state"],
                district=config["district"],
                country=config.get("country", "India"),
                cluster_name=config.get("cluster_name"),
                fence_radius_m=config.get("fence_radius_m", 1500.0),
                boundary_geojson=config.get("boundary_geojson")
            )
            db.add(new_fac)

        # 2. Register in Plant & Site Hierarchy
        existing_plant = db.query(PlantModel).filter(PlantModel.id == facility_id).first()
        if existing_plant:
            existing_plant.name = config["name"]
            existing_plant.center_lat = config["center_lat"]
            existing_plant.center_lon = config["center_lon"]
        else:
            new_plant = PlantModel(
                id=facility_id,
                name=config["name"],
                industry_type=config.get("facility_type", "PETROCHEMICAL"),
                location=f"{config['district']}, {config['state']}",
                center_lat=config["center_lat"],
                center_lon=config["center_lon"],
                bounds_json=config.get("boundary_geojson", {}).get("coordinates", []),
                risk_level=config.get("risk_level", "High"),
                erdmp_license=config.get("erdmp_license")
            )
            db.add(new_plant)

        # 3. Register Assets
        for a in config.get("assets", []):
            existing_asset = db.query(AssetModel).filter(AssetModel.id == a["id"]).first()
            if not existing_asset:
                new_asset = AssetModel(
                    id=a["id"],
                    name=a["name"],
                    type=a.get("asset_type", "PROCESS_UNIT"),
                    sector=config.get("district", "General Industrial"),
                    lat=a["lat"],
                    lon=a["lon"],
                    chemical_id=a.get("chemical_id", "CHEM-GENERIC"),
                    capacity_m3=a.get("capacity_m3", 1000.0),
                    current_fill_pct=a.get("current_fill_pct", 50.0),
                    operating_pressure_bar=a.get("pressure_bar", 1.0),
                    operating_temp_c=a.get("temperature_c", 25.0)
                )
                db.add(new_asset)


        # 4. Register Sensors
        for s in config.get("sensors", []):
            existing_sensor = db.query(SensorMetadataModel).filter(
                SensorMetadataModel.sensor_id == s["sensor_id"]
            ).first()
            if not existing_sensor:
                new_sensor = SensorMetadataModel(
                    sensor_id=s["sensor_id"],
                    facility_id=facility_id,
                    asset_id=s.get("asset_id", "AST-GENERIC"),
                    tag_name=s["tag_name"],
                    sensor_type=s["sensor_type"],
                    unit=s["unit"],
                    valid_range_min=s.get("valid_range_min", 0.0),
                    valid_range_max=s.get("valid_range_max", 1000.0),
                    critical_max=s.get("critical_max", 500.0)
                )
                db.add(new_sensor)

        # 5. Log Audit Record
        audit_entry = DecisionAuditModel(
            id=f"AUD-ONB-{uuid.uuid4().hex[:12]}",
            incident_id="FACILITY-ONBOARDING",
            module="SITE_REGISTRY",
            input_summary=f"Onboarding facility {config['name']} ({facility_id})",
            recommendation="Register facility, units, assets, sensors, and hazard profiles",
            reason="Enterprise multi-facility expansion",
            human_action="APPROVED",
            actor_role="PLANT_MANAGER",
            actor_name="Enterprise Facility Administrator",
            result=json.dumps({"facility_id": facility_id, "status": "ONBOARDED"}),
            status="EXECUTED"
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "success",
            "facility_id": facility_id,
            "name": config["name"],
            "state": config["state"],
            "assets_registered": len(config.get("assets", [])),
            "sensors_registered": len(config.get("sensors", [])),
            "onboarded_at_utc": datetime.now(timezone.utc).isoformat()
        }
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="REACT-X Facility Onboarding Utility")
    parser.add_argument("--config", type=Path, required=True, help="Path to facility JSON definition")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without writing to DB")
    args = parser.parse_args()

    try:
        res = onboard_facility(args.config, args.dry_run)
        print("[SUCCESS] Facility Onboarding Completed:")
        print(json.dumps(res, indent=2))
    except Exception as ex:
        print(f"[ERROR] Facility onboarding failed: {ex}", file=sys.stderr)
        sys.exit(1)

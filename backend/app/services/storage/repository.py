import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.storage_models import (
    PlantOperatingLimitModel, SensorTelemetryRecord, IncidentPacketModel, LineageRecordModel
)
from app.schemas.canonical import CanonicalEvent

class StorageRepository:
    """
    Unified database repository DAO for telemetry, operating limits, and provenance lineage.
    """
    def seed_default_operating_limits(self, db: Session):
        count = db.query(PlantOperatingLimitModel).count()
        if count > 0:
            return

        limits = [
            PlantOperatingLimitModel(
                id="POL-T04-P", asset_id="T-04", chemical_id="CHEM-NH3", signal_id="T04_PRESS_01", unit="bar",
                nominal_low=3.8, nominal_high=4.8, warning_low=2.8, warning_high=5.5, critical_low=1.5, critical_high=6.5,
                source_document="Dahej Ammonia Tank Operating License (PESO/IND/2024)", verified_by="Er. R. K. Sharma (Process Safety Lead)"
            ),
            PlantOperatingLimitModel(
                id="POL-T04-T", asset_id="T-04", chemical_id="CHEM-NH3", signal_id="T04_TEMP_SKIN", unit="degC",
                nominal_low=-34.0, nominal_high=-31.0, warning_low=-38.0, warning_high=-25.0, critical_low=-42.0, critical_high=-10.0,
                source_document="Dahej Ammonia Tank Operating License (PESO/IND/2024)", verified_by="Er. R. K. Sharma (Process Safety Lead)"
            ),
            PlantOperatingLimitModel(
                id="POL-T04-V", asset_id="T-04", chemical_id="CHEM-NH3", signal_id="T04_VIB_RMS", unit="mm/s",
                nominal_low=0.5, nominal_high=2.5, warning_low=0.0, warning_high=5.0, critical_low=0.0, critical_high=7.5,
                source_document="ISO 10816-3 Mechanical Vibration Standard", verified_by="Chief Mechanical Engineer"
            ),
            PlantOperatingLimitModel(
                id="POL-T03-P", asset_id="T-03", chemical_id="CHEM-LPG", signal_id="T03_PRESS_01", unit="bar",
                nominal_low=9.0, nominal_high=12.5, warning_low=6.0, warning_high=15.0, critical_low=3.0, critical_high=18.0,
                source_document="OISD-STD-144 Liquefied Petroleum Gas Storage", verified_by="Safety Director"
            )
        ]
        for l in limits:
            db.add(l)
        db.commit()

    def get_operating_limits_for_asset(self, db: Session, asset_id: str) -> List[PlantOperatingLimitModel]:
        self.seed_default_operating_limits(db)
        return db.query(PlantOperatingLimitModel).filter(PlantOperatingLimitModel.asset_id == asset_id).all()

    def record_lineage(
        self,
        db: Session,
        source: str,
        source_type: str,
        processing_stage: str,
        transformation: str,
        final_decision: str,
        device_id: Optional[str] = None,
        operator_role: Optional[str] = None
    ) -> LineageRecordModel:
        rec = LineageRecordModel(
            id=f"LIN-{uuid.uuid4().hex[:8].upper()}",
            source=source,
            source_type=source_type,
            device_id=device_id,
            operator_role=operator_role,
            processing_stage=processing_stage,
            transformation=transformation,
            final_decision=final_decision,
            timestamp=datetime.utcnow()
        )
        db.add(rec)
        db.commit()
        return rec

    def persist_incident_packet(
        self,
        db: Session,
        packet_dict: Dict[str, Any]
    ) -> IncidentPacketModel:
        inc = IncidentPacketModel(
            incident_id=packet_dict.get("incident_id", f"INC-{uuid.uuid4().hex[:6].upper()}"),
            hazard_type=packet_dict.get("hazard_type", "TOXIC_RELEASE"),
            risk_score=float(packet_dict.get("risk_score", 50.0)),
            confidence=float(packet_dict.get("confidence", 1.0)),
            affected_zone=packet_dict.get("affected_zone", "Plant Sector"),
            status=packet_dict.get("status", "OPEN"),
            source_asset_id=packet_dict.get("source_asset_id", "T-04"),
            chemical_id=packet_dict.get("chemical_id", "CHEM-NH3"),
            evidence_json=packet_dict.get("evidence", {}),
            recommendations_json=packet_dict.get("recommendations", [])
        )
        db.merge(inc)
        db.commit()
        return inc

storage_repository = StorageRepository()

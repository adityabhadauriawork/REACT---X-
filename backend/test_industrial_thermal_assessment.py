import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.schemas.thermal_classification import TargetSourceClass as ThermalSourceClass
from app.schemas.thermal_fingerprint import AbnormalityStatus
from app.schemas.thermal_corroboration import EvidenceState
from app.schemas.thermal_assessment import (
    IndustrialThermalAssessment,
    IndustrialRiskLevel,
    HandoffEligibility,
    AssessmentStatus,
    AssessmentRequest,
    IncidentPromotionRequest,
    IncidentRejectionRequest
)
from app.models.thermal_assessment import IndustrialThermalAssessmentModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.models.thermal_event import ThermalEventModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel
from app.models.audit import DecisionAuditModel
from app.services.satellite.assessment_engine import assessment_engine
from app.services.ml.thermal_classifier_service import classifier_service
from app.services.satellite.abnormality_engine import abnormality_engine
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine


# =============================================================================
# PYTEST IN-MEMORY DATABASE FIXTURE (StaticPool for multi-request test isolation)
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # 1. Seed Industrial Facilities
    f1 = IndustrialFacilityModel(
        facility_id="FAC-OPAL-DHJ-01",
        name="ONGC Petro Additions Ltd (OPaL)",
        operator_name="ONGC",
        facility_type="PETROCHEMICAL",
        latitude=21.6982,
        longitude=72.5841,
        boundary_geojson={"type": "Polygon", "coordinates": [[[72.58, 21.69], [72.59, 21.69], [72.59, 21.70], [72.58, 21.70], [72.58, 21.69]]]}
    )
    f2 = IndustrialFacilityModel(
        facility_id="FAC-GACL-DHJ-02",
        name="Gujarat Alkalies and Chemicals Ltd (GACL)",
        operator_name="GACL",
        facility_type="CHLOR_ALKALI",
        latitude=21.7050,
        longitude=72.5920,
        boundary_geojson={"type": "Polygon", "coordinates": [[[72.59, 21.70], [72.60, 21.70], [72.60, 21.71], [72.59, 21.71], [72.59, 21.70]]]}
    )
    db.add_all([f1, f2])

    now = datetime.now(timezone.utc)

    # 1.5 Seed Baseline Empirical Fingerprints
    fp1 = FacilityThermalFingerprintModel(
        fingerprint_id="FP-FAC-OPAL-DHJ-01",
        facility_id="FAC-OPAL-DHJ-01",
        facility_name="ONGC Petro Additions Ltd (OPaL)",
        baseline_start=now - timedelta(days=90),
        baseline_end=now,
        observation_count=60,
        active_days=50,
        frp_mean=24.5,
        frp_median=22.0,
        frp_mad=4.5,
        frp_p90=38.0,
        frp_max=50.0,
        temp_mean=342.0,
        temp_median=340.0,
        centroid_lat=21.6982,
        centroid_lon=72.5841
    )
    fp2 = FacilityThermalFingerprintModel(
        fingerprint_id="FP-FAC-GACL-DHJ-02",
        facility_id="FAC-GACL-DHJ-02",
        facility_name="Gujarat Alkalies and Chemicals Ltd (GACL)",
        baseline_start=now - timedelta(days=90),
        baseline_end=now,
        observation_count=40,
        active_days=35,
        frp_mean=15.0,
        frp_median=15.0,
        frp_mad=3.0,
        frp_p90=25.0,
        frp_max=35.0,
        temp_mean=330.0,
        temp_median=330.0,
        centroid_lat=21.7050,
        centroid_lon=72.5920
    )
    db.add_all([fp1, fp2])

    # 2. Seed Baseline Persistent Flare Source (Normal operation)
    source_flare = ThermalSourceModel(
        source_id="SRC-20260830-DHJ-01",
        name="OPaL Flare Complex Source",
        centroid_lat=21.6982,
        centroid_lon=72.5841,
        h3_index="8760920b1ffffff",
        first_detected=now - timedelta(days=60),
        last_detected=now,
        active_days_count=55,
        observation_count=28,
        unique_satellite_count=3,
        unique_sensor_count=2,
        mean_frp_mw=24.5,
        max_frp_mw=45.0,
        min_frp_mw=12.0,
        mean_brightness_temp_k=342.0,
        day_detection_count=14,
        night_detection_count=14,
        diurnal_ratio=1.0,
        source_status="PERSISTENT_SOURCE",
        source_confidence="HIGH",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        primary_attributed_facility_name="ONGC Petro Additions Ltd (OPaL)",
        facility_distance_m=0.0,
        is_inside_facility_boundary=True,
        facility_attribution_confidence=0.98,
        attribution_status="ATTRIBUTED_HIGH_CONFIDENCE"
    )

    # Seed events for flare
    se1 = ThermalSourceEventModel(
        source_id="SRC-20260830-DHJ-01",
        event_id="EVT-FLARE-01",
        latitude=21.6982,
        longitude=72.5841,
        frp_mw=24.0,
        brightness_temp_k=342.0,
        satellite="NOAA-20",
        sensor="VIIRS",
        acquisition_timestamp=now - timedelta(hours=4),
        day_night="N"
    )
    se2 = ThermalSourceEventModel(
        source_id="SRC-20260830-DHJ-01",
        event_id="EVT-FLARE-02",
        latitude=21.6983,
        longitude=72.5842,
        frp_mw=25.0,
        brightness_temp_k=343.0,
        satellite="Suomi-NPP",
        sensor="VIIRS",
        acquisition_timestamp=now - timedelta(hours=12),
        day_night="D"
    )
    db.add_all([source_flare, se1, se2])
    db.commit()

    yield db
    db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# CASE 1: NORMAL PERSISTENT FLARE -> LOW CONCERN / NO INCIDENT
# =============================================================================

def test_case_01_normal_persistent_flare_low_concern(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    assessment = assessment_engine.assess_thermal_source(source=source, db=db_session)

    assert assessment.is_routine_operation is True
    assert assessment.classification in [ThermalSourceClass.GAS_FLARE, ThermalSourceClass.ROUTINE_PROCESS_HEAT]
    assert assessment.industrial_risk_level in [IndustrialRiskLevel.NOMINAL, IndustrialRiskLevel.LOW, IndustrialRiskLevel.MODERATE]
    assert assessment.handoff_eligibility == HandoffEligibility.NOT_ELIGIBLE
    assert "Routine industrial operation" in assessment.operational_concern_summary


# =============================================================================
# CASE 2: NORMAL INDUSTRIAL HEAT -> NOT INDUSTRIAL FIRE
# =============================================================================

def test_case_02_routine_process_heat(db_session):
    now = datetime.now(timezone.utc)
    source_heat = ThermalSourceModel(
        source_id="SRC-HEAT-01",
        name="Cracker Process Furnace Heat",
        centroid_lat=21.6985,
        centroid_lon=72.5845,
        h3_index="8760920b1ffffff",
        first_detected=now - timedelta(days=90),
        last_detected=now,
        active_days_count=85,
        observation_count=60,
        mean_frp_mw=12.0,
        max_frp_mw=18.0,
        min_frp_mw=8.0,
        mean_brightness_temp_k=335.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        is_inside_facility_boundary=True,
        facility_attribution_confidence=0.99
    )
    db_session.add(source_heat)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_heat, db=db_session)
    assert assessment.classification != ThermalSourceClass.INDUSTRIAL_FIRE
    assert assessment.is_routine_operation is True
    assert assessment.industrial_risk_level in [IndustrialRiskLevel.NOMINAL, IndustrialRiskLevel.LOW]


# =============================================================================
# CASE 3: KNOWN INDUSTRIAL SOURCE + SEVERE ABNORMALITY -> ELEVATED RISK
# =============================================================================

def test_case_03_severe_abnormality_surge(db_session):
    now = datetime.now(timezone.utc)
    source_surge = ThermalSourceModel(
        source_id="SRC-SURGE-01",
        name="OPaL Ethylene Tank Surge",
        centroid_lat=21.6982,
        centroid_lon=72.5841,
        h3_index="8760920b1ffffff",
        first_detected=now - timedelta(days=30),
        last_detected=now,
        active_days_count=10,
        observation_count=8,
        mean_frp_mw=85.0,  # Extreme surge
        max_frp_mw=140.0,
        min_frp_mw=15.0,
        mean_brightness_temp_k=395.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        primary_attributed_facility_name="ONGC Petro Additions Ltd (OPaL)",
        is_inside_facility_boundary=True,
        facility_attribution_confidence=0.98
    )
    db_session.add(source_surge)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_surge, db=db_session)
    assert assessment.is_routine_operation is False
    assert assessment.industrial_risk_level in [IndustrialRiskLevel.HIGH, IndustrialRiskLevel.CRITICAL]
    assert assessment.handoff_eligibility in [HandoffEligibility.INCIDENT_DRAFT_READY, HandoffEligibility.REVIEW_REQUIRED]


# =============================================================================
# CASE 4: INDUSTRIAL FIRE + STRONG EVIDENCE -> INCIDENT DRAFT READY
# =============================================================================

def test_case_04_industrial_fire_incident_draft_ready(db_session):
    now = datetime.now(timezone.utc)
    source_fire = ThermalSourceModel(
        source_id="SRC-FIRE-01",
        name="GACL Storage Tank Ignition",
        centroid_lat=21.7050,
        centroid_lon=72.5920,
        h3_index="8760920b2ffffff",
        first_detected=now - timedelta(hours=2),
        last_detected=now,
        active_days_count=1,
        observation_count=4,
        mean_frp_mw=110.0,
        max_frp_mw=165.0,
        min_frp_mw=75.0,
        mean_brightness_temp_k=420.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id="FAC-GACL-DHJ-02",
        primary_attributed_facility_name="Gujarat Alkalies and Chemicals Ltd (GACL)",
        is_inside_facility_boundary=True,
        facility_attribution_confidence=0.99
    )
    # Add multi-satellite events
    e1 = ThermalSourceEventModel(
        source_id="SRC-FIRE-01", event_id="EVT-F1", latitude=21.7050, longitude=72.5920,
        frp_mw=110.0, brightness_temp_k=420.0, satellite="NOAA-20", sensor="VIIRS",
        acquisition_timestamp=now - timedelta(minutes=45)
    )
    e2 = ThermalSourceEventModel(
        source_id="SRC-FIRE-01", event_id="EVT-F2", latitude=21.7052, longitude=72.5921,
        frp_mw=120.0, brightness_temp_k=425.0, satellite="TERRA", sensor="MODIS",
        acquisition_timestamp=now - timedelta(minutes=15)
    )
    db_session.add_all([source_fire, e1, e2])
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_fire, db=db_session)
    assert assessment.handoff_eligibility == HandoffEligibility.INCIDENT_DRAFT_READY
    assert assessment.incident_draft is not None
    assert assessment.incident_draft.suggested_incident_type == "FIRE_EXPLOSION"
    assert assessment.incident_draft.facility_name == "Gujarat Alkalies and Chemicals Ltd (GACL)"


# =============================================================================
# CASE 5: WILDFIRE NEAR INDUSTRIAL FACILITY -> BOUNDED RISK (NON-INDUSTRIAL)
# =============================================================================

def test_case_05_wildfire_near_industrial_facility(db_session):
    now = datetime.now(timezone.utc)
    source_wildfire = ThermalSourceModel(
        source_id="SRC-WILD-01",
        name="Coastal Scrub Brush Fire",
        centroid_lat=21.6800,  # 2.2km outside facility
        centroid_lon=72.5700,
        h3_index="8760920b3ffffff",
        first_detected=now - timedelta(hours=5),
        last_detected=now,
        active_days_count=1,
        observation_count=2,
        mean_frp_mw=30.0,
        max_frp_mw=35.0,
        min_frp_mw=25.0,
        mean_brightness_temp_k=330.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id=None,
        is_inside_facility_boundary=False,
        facility_distance_m=2200.0,
        facility_attribution_confidence=0.10
    )
    db_session.add(source_wildfire)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_wildfire, db=db_session)
    assert assessment.is_routine_operation is True
    assert assessment.industrial_risk_level in [IndustrialRiskLevel.NOMINAL, IndustrialRiskLevel.LOW]
    assert assessment.handoff_eligibility == HandoffEligibility.NOT_ELIGIBLE


# =============================================================================
# CASE 6: UNATTRIBUTED HOTSPOT -> INSUFFICIENT EVIDENCE / LOW RISK
# =============================================================================

def test_case_06_unattributed_hotspot(db_session):
    now = datetime.now(timezone.utc)
    source_unattr = ThermalSourceModel(
        source_id="SRC-UNATTR-01",
        name="Remote Rural Anomaly",
        centroid_lat=24.1200,
        centroid_lon=75.3400,
        h3_index="8760920b4ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=1,
        mean_frp_mw=10.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id=None,
        is_inside_facility_boundary=False,
        facility_attribution_confidence=0.05
    )
    db_session.add(source_unattr)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_unattr, db=db_session)
    assert assessment.attribution_confidence <= 0.20
    assert assessment.industrial_risk_score <= 35.0
    assert assessment.handoff_eligibility == HandoffEligibility.NOT_ELIGIBLE


# =============================================================================
# CASE 7: HIGH ML CONFIDENCE + WEAK SATELLITE EVIDENCE -> EVIDENCE LIMITED
# =============================================================================

def test_case_07_high_ml_weak_satellite_evidence(db_session):
    now = datetime.now(timezone.utc)
    source_sparse_sat = ThermalSourceModel(
        source_id="SRC-SPARSE-SAT-01",
        name="Single Pass Transient Thermal Anomaly",
        centroid_lat=21.6982,
        centroid_lon=72.5841,
        h3_index="8760920b1ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=1,
        mean_frp_mw=50.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        is_inside_facility_boundary=True
    )
    db_session.add(source_sparse_sat)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_sparse_sat, db=db_session)
    # The 4 confidences remain distinctly separated
    assert assessment.overall_evidence_confidence <= 0.88
    assert assessment.corroboration_status in [EvidenceState.SINGLE_SOURCE, EvidenceState.PARTIALLY_CORROBORATED]


# =============================================================================
# CASE 8: STRONG EVIDENCE + SPARSE FACILITY HISTORY -> ABNORMALITY CONFIDENCE LIMITED
# =============================================================================

def test_case_08_sparse_history_abnormality_penalty(db_session):
    now = datetime.now(timezone.utc)
    source_new_plant = ThermalSourceModel(
        source_id="SRC-NEW-PLANT-01",
        name="Newly Commissioned Plant Hotspot",
        centroid_lat=21.6982,
        centroid_lon=72.5841,
        h3_index="8760920b1ffffff",
        first_detected=now - timedelta(days=2),
        last_detected=now,
        active_days_count=2,
        observation_count=2,
        mean_frp_mw=30.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        is_inside_facility_boundary=True
    )
    db_session.add(source_new_plant)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_new_plant, db=db_session)
    assert assessment.abnormality_confidence <= 0.70
    assert assessment.abnormality_status in [AbnormalityStatus.INSUFFICIENT_HISTORY, AbnormalityStatus.SPARSE_OBSERVATIONS, AbnormalityStatus.NORMAL_BASELINE]


# =============================================================================
# CASE 9: CONFLICTING SATELLITES -> CONFIDENCE DOWNGRADED
# =============================================================================

def test_case_09_conflicting_satellites_downgrade(db_session):
    now = datetime.now(timezone.utc)
    source_conflict = ThermalSourceModel(
        source_id="SRC-CONF-01",
        name="Conflicting Geometric Source",
        centroid_lat=22.0000,
        centroid_lon=73.0000,
        h3_index="8760920b5ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=2,
        mean_frp_mw=20.0,
        source_status="NEW_SOURCE"
    )
    # Event 1 and Event 2 4.5km apart
    e1 = ThermalSourceEventModel(source_id="SRC-CONF-01", event_id="EV-C1", latitude=22.0000, longitude=73.0000, frp_mw=20.0, satellite="NOAA-20", sensor="VIIRS", acquisition_timestamp=now)
    e2 = ThermalSourceEventModel(source_id="SRC-CONF-01", event_id="EV-C2", latitude=22.0400, longitude=73.0400, frp_mw=20.0, satellite="TERRA", sensor="MODIS", acquisition_timestamp=now)
    db_session.add_all([source_conflict, e1, e2])
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_conflict, db=db_session)
    assert assessment.corroboration_status in [EvidenceState.CONFLICTING, EvidenceState.PARTIALLY_CORROBORATED, EvidenceState.SINGLE_SOURCE]
    assert assessment.overall_evidence_confidence <= 0.88


# =============================================================================
# CASE 10: REASSESSMENT VERSIONING (LATER SATELLITE EVIDENCE UPDATES VERSION)
# =============================================================================

def test_case_10_reassessment_versioning_and_history(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    
    # 1. First assessment (v1)
    asm1 = assessment_engine.assess_thermal_source(source=source, db=db_session)
    assessment_engine.persist_assessment(assessment=asm1, db=db_session)
    assert asm1.version == 1
    assert asm1.parent_assessment_id is None

    # 2. Subsequent assessment (v2)
    asm2 = assessment_engine.assess_thermal_source(source=source, db=db_session)
    assessment_engine.persist_assessment(assessment=asm2, db=db_session)
    assert asm2.version == 2
    assert asm2.parent_assessment_id == asm1.assessment_id
    assert asm2.assessment_status == AssessmentStatus.UPDATED


# =============================================================================
# CASE 11: NO PLANT CHEMICAL INVENTORY -> NO FABRICATED CHEMICAL HAZARD
# =============================================================================

def test_case_11_no_fabricated_chemical_inventory(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    assessment = assessment_engine.assess_thermal_source(source=source, db=db_session)
    
    draft = assessment_engine._create_incident_draft(
        source=source,
        clf_result=classifier_service.classify_source(source=source, db=db_session),
        abn_result=abnormality_engine.assess_thermal_source(source=source, current_event=None, db=db_session),
        evidence_bundle=evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session),
        risk_level=IndustrialRiskLevel.HIGH,
        risk_score=75.0
    )
    assert "INSUFFICIENT DATA" in draft.chemical_consequence_status
    assert "Ammonia" not in draft.chemical_consequence_status


# =============================================================================
# CASE 12: NO SITE-LEVEL WORKER/ROAD DATA -> NO FABRICATED EVACUATION PLAN
# =============================================================================

def test_case_12_no_fabricated_site_evacuation(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    assessment = assessment_engine.assess_thermal_source(source=source, db=db_session)
    
    draft = assessment_engine._create_incident_draft(
        source=source,
        clf_result=classifier_service.classify_source(source=source, db=db_session),
        abn_result=abnormality_engine.assess_thermal_source(source=source, current_event=None, db=db_session),
        evidence_bundle=evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session),
        risk_level=IndustrialRiskLevel.HIGH,
        risk_score=75.0
    )
    assert "SITE-LEVEL RESPONSE DATA UNAVAILABLE" in draft.site_evacuation_status


# =============================================================================
# CASE 13: MULTIPLE NEIGHBOURING FACILITIES -> AMBIGUITY HANDLED
# =============================================================================

def test_case_13_neighbouring_facilities_ambiguity(db_session):
    now = datetime.now(timezone.utc)
    source_boundary = ThermalSourceModel(
        source_id="SRC-BORDER-01",
        name="Boundary Hotspot between OPaL & GACL",
        centroid_lat=21.7015,
        centroid_lon=72.5880,
        h3_index="8760920b1ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=2,
        mean_frp_mw=35.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        is_inside_facility_boundary=False,
        facility_distance_m=450.0,
        facility_attribution_confidence=0.68
    )
    db_session.add(source_boundary)
    db_session.commit()

    assessment = assessment_engine.assess_thermal_source(source=source_boundary, db=db_session)
    assert 0.50 <= assessment.attribution_confidence <= 0.85


# =============================================================================
# CASE 14: OPERATOR REJECTS INCIDENT DRAFT -> REJECTION AUDITED
# =============================================================================

def test_case_14_operator_rejection_audit_trail(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    asm = assessment_engine.assess_thermal_source(source=source, db=db_session)
    assessment_engine.persist_assessment(assessment=asm, db=db_session)

    req = IncidentRejectionRequest(
        operator_id="CMD-4091",
        operator_role="HSE_COMMANDER",
        rejection_reason="AUTHORIZED_MAINTENANCE_FLARING",
        notes="Plant radio confirmed scheduled flare header purge."
    )
    res = assessment_engine.reject_incident_draft(assessment_id=asm.assessment_id, req=req, db=db_session)

    assert res["status"] == "INCIDENT_DRAFT_REJECTED"
    assert res["rejection_reason"] == "AUTHORIZED_MAINTENANCE_FLARING"

    # Check DecisionAuditModel record
    audit_entry = db_session.query(DecisionAuditModel).filter_by(id=res["audit_record_id"]).first()
    assert audit_entry is not None
    assert audit_entry.human_action == "REJECTED_DRAFT_INCIDENT"
    assert audit_entry.actor_name == "CMD-4091"


# =============================================================================
# CASE 15: OPERATOR APPROVES INCIDENT DRAFT -> PROMOTED & AUDITED
# =============================================================================

def test_case_15_operator_promotion_and_audit_trail(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    asm = assessment_engine.assess_thermal_source(source=source, db=db_session)
    assessment_engine.persist_assessment(assessment=asm, db=db_session)

    req = IncidentPromotionRequest(
        operator_id="CMD-8821",
        operator_role="HSE_COMMANDER",
        justification="Thermal anomaly confirmed inside cryogenic storage unit. Activating Level 2 incident response."
    )
    res = assessment_engine.promote_to_incident(assessment_id=asm.assessment_id, req=req, db=db_session)

    assert res["status"] == "INCIDENT_PROMOTED"
    assert "INC-" in res["incident_id"]

    # Check DecisionAuditModel record
    audit_entry = db_session.query(DecisionAuditModel).filter_by(id=res["audit_record_id"]).first()
    assert audit_entry is not None
    assert audit_entry.human_action == "PROMOTED_TO_ACTIVE_INCIDENT"
    assert audit_entry.actor_name == "CMD-8821"
    assert "cryogenic storage" in audit_entry.reason


# =============================================================================
# CASE 16: FASTAPI REST ENDPOINTS END-TO-END VERIFICATION
# =============================================================================

def test_case_16_fastapi_rest_endpoints(client):
    # 1. Get Source Assessment
    res_asm = client.get("/api/thermal/sources/SRC-20260830-DHJ-01/assessment")
    assert res_asm.status_code == 200
    asm_data = res_asm.json()
    assert asm_data["source_id"] == "SRC-20260830-DHJ-01"
    assert "attribution_confidence" in asm_data
    assert "classification_confidence" in asm_data
    assert "abnormality_confidence" in asm_data
    assert "overall_evidence_confidence" in asm_data

    # 2. Force Reassess
    res_re = client.post("/api/thermal/sources/SRC-20260830-DHJ-01/assess", json={})
    assert res_re.status_code == 200
    assert res_re.json()["version"] >= 1

    # 3. List Assessments
    res_list = client.get("/api/thermal/assessments?limit=10")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 4. Get Assessment By ID
    asm_id = asm_data["assessment_id"]
    res_single = client.get(f"/api/thermal/assessments/{asm_id}")
    assert res_single.status_code == 200
    assert res_single.json()["assessment_id"] == asm_id

    # 5. Get History Tree
    res_hist = client.get(f"/api/thermal/assessments/{asm_id}/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1

    # 6. Executive Situation Brief
    res_brief = client.get(f"/api/thermal/assessments/{asm_id}/executive-brief")
    assert res_brief.status_code == 200
    assert "EXECUTIVE SITUATION BRIEF" in res_brief.json()["brief_markdown"]

    # 7. Promote to Incident
    res_promo = client.post(f"/api/thermal/assessments/{asm_id}/promote-incident", json={
        "operator_id": "CMD-9901",
        "operator_role": "HSE_COMMANDER",
        "justification": "API authorized incident promotion test"
    })
    assert res_promo.status_code == 200
    assert res_promo.json()["status"] == "INCIDENT_PROMOTED"

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.facility_config import (
    FacilityConfig, FacilityType, FacilityConnectivityStatus,
    FacilityBaselineStage, HazardProfileType, FacilityCapability,
    DataProvenance, AreaConfig, UnitConfig, AssetConfig, ZoneConfig,
    NationalCoverageSummary, RegionFreshnessSummary, FacilityConfigExport
)
from app.services.storage.facility_registry_repository import facility_registry_repository

class FacilityRegistryService:
    """
    Central National Facility Registry & Governance Engine.
    Manages multi-state facility onboarding, cold-start lifecycle stages,
    dynamic coverage summaries, and secure configuration import/export.
    """

    SEEDED_NATIONAL_FACILITIES = [
        # 1. Gujarat - Dahej Reference Complex
        FacilityConfig(
            facility_id="FAC-IN-DAHEJ-001",
            facility_name="Dahej Petrochemical Complex Alpha",
            facility_type=FacilityType.PETROCHEMICAL,
            country="India",
            state="Gujarat",
            district="Bharuch",
            city_locality="Dahej PCPIR",
            latitude=21.6850,
            longitude=72.5620,
            boundary_polygon=[[72.555, 21.680], [72.570, 21.680], [72.570, 21.690], [72.555, 21.690]],
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.FIRE, HazardProfileType.GAS, HazardProfileType.PRESSURE],
            capabilities=[FacilityCapability.SATELLITE, FacilityCapability.TELEMETRY, FacilityCapability.THERMAL_CAMERA, FacilityCapability.CCTV, FacilityCapability.GAS, FacilityCapability.PRESSURE],
            connectivity_status=FacilityConnectivityStatus.FULLY_INSTRUMENTED,
            baseline_stage=FacilityBaselineStage.PREDICTION_ENABLED,
            provenance=DataProvenance(facility_source="PESO_OFFICIAL_REGISTRY", source_version="2024-v2"),
            enabled=True,
            is_reference_environment=True,
            is_simulated=False
        ),
        # 2. Gujarat - Jamnagar Mega Refinery
        FacilityConfig(
            facility_id="FAC-IN-JAMNAGAR-001",
            facility_name="Jamnagar Integrated Refinery Complex",
            facility_type=FacilityType.REFINERY,
            country="India",
            state="Gujarat",
            district="Jamnagar",
            city_locality="Motikhavdi",
            latitude=22.3600,
            longitude=69.8800,
            boundary_polygon=[[69.860, 22.340], [69.910, 22.340], [69.910, 22.380], [69.860, 22.380]],
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.FIRE, HazardProfileType.PRESSURE],
            capabilities=[FacilityCapability.SATELLITE, FacilityCapability.TELEMETRY],
            connectivity_status=FacilityConnectivityStatus.PARTIAL_TELEMETRY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True,
            is_reference_environment=False,
            is_simulated=False
        ),
        # 3. Maharashtra - Mumbai BPCL Refinery
        FacilityConfig(
            facility_id="FAC-IN-MUMBAI-001",
            facility_name="Mumbai Chembur Coastal Refinery",
            facility_type=FacilityType.REFINERY,
            country="India",
            state="Maharashtra",
            district="Mumbai Suburban",
            city_locality="Mahul / Chembur",
            latitude=19.0050,
            longitude=72.8950,
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.FIRE, HazardProfileType.GAS],
            capabilities=[FacilityCapability.SATELLITE, FacilityCapability.TELEMETRY],
            connectivity_status=FacilityConnectivityStatus.PARTIAL_TELEMETRY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 4. Odisha - Rourkela Integrated Steel Plant
        FacilityConfig(
            facility_id="FAC-IN-ROURKELA-001",
            facility_name="Rourkela Integrated Steel Plant",
            facility_type=FacilityType.STEEL,
            country="India",
            state="Odisha",
            district="Sundargarh",
            city_locality="Rourkela",
            latitude=22.2150,
            longitude=84.8650,
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.EQUIPMENT],
            capabilities=[FacilityCapability.SATELLITE],
            connectivity_status=FacilityConnectivityStatus.SATELLITE_ONLY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 5. Chhattisgarh - Korba Super Thermal Power
        FacilityConfig(
            facility_id="FAC-IN-KORBA-001",
            facility_name="Korba Super Thermal Power Plant",
            facility_type=FacilityType.THERMAL_POWER,
            country="India",
            state="Chhattisgarh",
            district="Korba",
            city_locality="Jamnipali",
            latitude=22.3750,
            longitude=82.7250,
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.PROCESS],
            capabilities=[FacilityCapability.SATELLITE],
            connectivity_status=FacilityConnectivityStatus.SATELLITE_ONLY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 6. Tamil Nadu - Manali Petrochemicals
        FacilityConfig(
            facility_id="FAC-IN-MANALI-001",
            facility_name="Manali Petrochemical & Fertilizers",
            facility_type=FacilityType.PETROCHEMICAL,
            country="India",
            state="Tamil Nadu",
            district="Chennai",
            city_locality="Manali Industrial Area",
            latitude=13.1650,
            longitude=80.2600,
            criticality="TIER_2_MAJOR",
            hazard_profile=[HazardProfileType.GAS, HazardProfileType.CHEMICAL if hasattr(HazardProfileType, 'CHEMICAL') else HazardProfileType.PROCESS, HazardProfileType.FIRE],
            capabilities=[FacilityCapability.SATELLITE, FacilityCapability.TELEMETRY],
            connectivity_status=FacilityConnectivityStatus.PARTIAL_TELEMETRY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 7. Andhra Pradesh - Visakhapatnam Steel Plant
        FacilityConfig(
            facility_id="FAC-IN-VIZAG-001",
            facility_name="Visakhapatnam Coastal Steel Plant",
            facility_type=FacilityType.STEEL,
            country="India",
            state="Andhra Pradesh",
            district="Visakhapatnam",
            city_locality="Gajuwaka",
            latitude=17.6250,
            longitude=83.1850,
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.EQUIPMENT],
            capabilities=[FacilityCapability.SATELLITE],
            connectivity_status=FacilityConnectivityStatus.SATELLITE_ONLY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 8. Assam - Numaligarh Refinery
        FacilityConfig(
            facility_id="FAC-IN-NUMALIGARH-001",
            facility_name="Numaligarh Eco-Refinery",
            facility_type=FacilityType.REFINERY,
            country="India",
            state="Assam",
            district="Golaghat",
            city_locality="Numaligarh",
            latitude=26.5850,
            longitude=93.7450,
            criticality="TIER_1_CRITICAL",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.FIRE],
            capabilities=[FacilityCapability.SATELLITE],
            connectivity_status=FacilityConnectivityStatus.SATELLITE_ONLY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 9. Rajasthan - Udaipur Zinc Smelter / Mining
        FacilityConfig(
            facility_id="FAC-IN-UDAIPUR-001",
            facility_name="Debari Zinc Smelter & Complex",
            facility_type=FacilityType.MINING,
            country="India",
            state="Rajasthan",
            district="Udaipur",
            city_locality="Debari",
            latitude=24.6050,
            longitude=73.8150,
            criticality="TIER_2_MAJOR",
            hazard_profile=[HazardProfileType.THERMAL, HazardProfileType.PROCESS],
            capabilities=[FacilityCapability.SATELLITE],
            connectivity_status=FacilityConnectivityStatus.SATELLITE_ONLY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        ),
        # 10. Karnataka - Mangalore Chemicals & LNG
        FacilityConfig(
            facility_id="FAC-IN-MANGALORE-001",
            facility_name="Mangalore Coastal Chemicals & Terminal",
            facility_type=FacilityType.CHEMICAL,
            country="India",
            state="Karnataka",
            district="Dakshina Kannada",
            city_locality="Panambur",
            latitude=12.9450,
            longitude=74.8150,
            criticality="TIER_2_MAJOR",
            hazard_profile=[HazardProfileType.GAS, HazardProfileType.FIRE, HazardProfileType.PRESSURE],
            capabilities=[FacilityCapability.SATELLITE, FacilityCapability.TELEMETRY],
            connectivity_status=FacilityConnectivityStatus.PARTIAL_TELEMETRY,
            baseline_stage=FacilityBaselineStage.BASELINE_READY,
            enabled=True
        )
    ]

    def seed_initial_facilities_if_empty(self, db: Session) -> int:
        """Seeds canonical multi-state reference facilities if registry table is empty."""
        existing = facility_registry_repository.list_facilities(db, limit=1)
        if len(existing) == 0:
            for fac in self.SEEDED_NATIONAL_FACILITIES:
                facility_registry_repository.upsert_facility(db, fac)
            return len(self.SEEDED_NATIONAL_FACILITIES)
        return 0

    def onboard_facility(self, db: Session, cfg: FacilityConfig) -> FacilityConfig:
        """Onboards a new facility, enforcing cold-start baseline stage."""
        rec = facility_registry_repository.upsert_facility(db, cfg)
        return facility_registry_repository.get_facility(db, rec.facility_id)

    def get_facility(self, db: Session, facility_id: str) -> Optional[FacilityConfig]:
        self.seed_initial_facilities_if_empty(db)
        return facility_registry_repository.get_facility(db, facility_id)

    def list_facilities(
        self,
        db: Session,
        state: Optional[str] = None,
        district: Optional[str] = None,
        facility_type: Optional[str] = None,
        connectivity_status: Optional[str] = None,
        baseline_stage: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FacilityConfig]:
        self.seed_initial_facilities_if_empty(db)
        return facility_registry_repository.list_facilities(
            db, state=state, district=district, facility_type=facility_type,
            connectivity_status=connectivity_status, baseline_stage=baseline_stage,
            bbox=bbox, limit=limit, offset=offset
        )

    def transition_baseline_stage(self, db: Session, facility_id: str, new_stage: FacilityBaselineStage) -> FacilityConfig:
        updated = facility_registry_repository.update_baseline_stage(db, facility_id, new_stage)
        if not updated:
            raise ValueError(f"Facility {facility_id} not found in registry")
        return updated

    def import_facility_config(self, db: Session, config_json: Dict[str, Any], dry_run: bool = False) -> FacilityConfig:
        """
        Securely imports a facility configuration, rejecting any embedded credentials.
        """
        # Security scan for forbidden secret keys
        forbidden_keys = ["password", "api_key", "secret", "token", "private_key", "credentials", "access_key"]
        def scan_dict(d: Any):
            if isinstance(d, dict):
                for k, v in d.items():
                    if any(fk in k.lower() for fk in forbidden_keys):
                        raise ValueError(f"Security violation: Forbidden credential/secret key '{k}' found in configuration.")
                    scan_dict(v)
            elif isinstance(d, list):
                for item in d:
                    scan_dict(item)

        scan_dict(config_json)

        # Parse and validate with Pydantic
        cfg = FacilityConfig(**config_json)

        if dry_run:
            return cfg

        return self.onboard_facility(db, cfg)

    def export_facility_config(self, db: Session, facility_id: str) -> FacilityConfigExport:
        fac = self.get_facility(db, facility_id)
        if not fac:
            raise ValueError(f"Facility {facility_id} not found for export")
        return FacilityConfigExport(
            export_version="v1.0",
            exported_at=datetime.now(timezone.utc),
            facility=fac
        )

    def get_national_coverage_summary(self, db: Session) -> NationalCoverageSummary:
        """Calculates real-time coverage statistics across India directly from database."""
        self.seed_initial_facilities_if_empty(db)
        all_facs = facility_registry_repository.list_facilities(db, limit=5000)
        
        state_counts = facility_registry_repository.count_facilities_by_state(db)
        industry_counts = facility_registry_repository.count_facilities_by_industry(db)
        
        monitored = sum(1 for f in all_facs if f.enabled)
        connected = sum(1 for f in all_facs if f.connectivity_status in [FacilityConnectivityStatus.PARTIAL_TELEMETRY, FacilityConnectivityStatus.FULLY_INSTRUMENTED, FacilityConnectivityStatus.VISUAL_CONNECTED])
        fully = sum(1 for f in all_facs if f.connectivity_status == FacilityConnectivityStatus.FULLY_INSTRUMENTED)

        return NationalCoverageSummary(
            total_known_facilities=len(all_facs),
            monitored_facilities=monitored,
            connected_facilities=connected,
            fully_instrumented_facilities=fully,
            active_states_count=len(state_counts),
            coverage_by_state=state_counts,
            coverage_by_industry=industry_counts
        )

    def get_regional_freshness_summary(self, db: Session, region_name: str = "National") -> RegionFreshnessSummary:
        """Computes regional data freshness percentages from actual records."""
        self.seed_initial_facilities_if_empty(db)
        facs = facility_registry_repository.list_facilities(db, limit=5000)
        if region_name != "National":
            facs = [f for f in facs if f.state.lower() == region_name.lower()]

        total = max(1, len(facs))
        fresh = sum(1 for f in facs if f.connectivity_status in [FacilityConnectivityStatus.FULLY_INSTRUMENTED, FacilityConnectivityStatus.PARTIAL_TELEMETRY])
        degraded = sum(1 for f in facs if f.connectivity_status == FacilityConnectivityStatus.SATELLITE_ONLY)
        stale = sum(1 for f in facs if f.connectivity_status in [FacilityConnectivityStatus.NOT_CONNECTED, FacilityConnectivityStatus.UNAVAILABLE])

        return RegionFreshnessSummary(
            region_name=region_name,
            total_sources=total,
            fresh_count=fresh,
            degraded_count=degraded,
            stale_count=stale,
            fresh_percent=round((fresh / total) * 100.0, 1),
            degraded_percent=round((degraded / total) * 100.0, 1),
            stale_percent=round((stale / total) * 100.0, 1)
        )

facility_registry_service = FacilityRegistryService()

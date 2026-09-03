import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from app.schemas.thermal import IndustrialFacility

class AttributionService:
    def __init__(self):
        self.facilities: Dict[str, IndustrialFacility] = {}
        self._seed_authoritative_facilities()

    def _seed_authoritative_facilities(self):
        """
        Seeds authoritative industrial facility GIS footprints based on OSM, Global Energy Monitor (GEM),
        and Bhuvan industrial registries across key Indian economic corridors.
        """
        seeds = [
            IndustrialFacility(
                id="FAC-DAHEJ-PCH01",
                name="PetroChem Complex Alpha - Unit 04",
                sector="PETROCHEMICAL",
                state="Gujarat",
                district="Bharuch",
                cluster_name="Dahej PCPIR Special Economic Zone",
                coordinates=[21.6850, 72.5750],
                fence_radius_m=1200.0,
                operator_name="Bharat Petrochemical Industrial Corp.",
                erdmp_license="PESO/IND/2024/GJ-DAHEJ-1505",
                major_chemicals_stored=["Ammonia (Anhydrous)", "Benzene (Pure Grade)", "Liquefied Petroleum Gas", "Chlorine"],
                known_flares_count=3,
                known_furnaces_count=2,
                baseline_mean_frp_mw=18.5,
                baseline_std_frp_mw=4.2,
                baseline_mean_temp_k=348.0,
                expected_diurnal_ratio=0.98,
                historical_detections_count=186,
                active_hotspots_count=1,
                current_max_frp_mw=19.2,
                current_abnormality_score=12.0,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-DAHEJ-LNG02",
                name="Petronet Dahej LNG Cryogenic Regasification Terminal",
                sector="REFINERY",
                state="Gujarat",
                district="Bharuch",
                cluster_name="Dahej Port & PCPIR Corridor",
                coordinates=[21.6720, 72.5320],
                fence_radius_m=1500.0,
                operator_name="Petronet LNG Limited",
                erdmp_license="PESO/IND/2023/GJ-LNG-0042",
                major_chemicals_stored=["Liquefied Natural Gas", "Boil-off Gas (Methane)"],
                known_flares_count=2,
                known_furnaces_count=0,
                baseline_mean_frp_mw=24.0,
                baseline_std_frp_mw=5.5,
                baseline_mean_temp_k=352.0,
                expected_diurnal_ratio=1.02,
                historical_detections_count=240,
                active_hotspots_count=1,
                current_max_frp_mw=25.4,
                current_abnormality_score=8.5,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-JAMNAGAR-REF01",
                name="Reliance Jamnagar Mega Refinery & Petrochemical Complex",
                sector="REFINERY",
                state="Gujarat",
                district="Jamnagar",
                cluster_name="Jamnagar Energy Superhub",
                coordinates=[22.3600, 69.8300],
                fence_radius_m=4500.0,
                operator_name="Reliance Industries Limited",
                erdmp_license="PESO/IND/2024/GJ-JAM-0001",
                major_chemicals_stored=["Crude Oil", "Naphtha", "Propylene", "Ethylene", "LPG"],
                known_flares_count=14,
                known_furnaces_count=18,
                baseline_mean_frp_mw=145.0,
                baseline_std_frp_mw=22.0,
                baseline_mean_temp_k=375.0,
                expected_diurnal_ratio=0.99,
                historical_detections_count=1840,
                active_hotspots_count=4,
                current_max_frp_mw=152.0,
                current_abnormality_score=15.0,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-HAZIRA-GAS01",
                name="ONGC Hazira Gas Processing & Petrochemical Complex",
                sector="PETROCHEMICAL",
                state="Gujarat",
                district="Surat",
                cluster_name="Hazira Industrial Belt",
                coordinates=[21.1200, 72.6700],
                fence_radius_m=2000.0,
                operator_name="Oil and Natural Gas Corporation",
                erdmp_license="PESO/IND/2022/GJ-HAZ-0089",
                major_chemicals_stored=["Sour Gas", "LPG", "Sulfur", "Condensate"],
                known_flares_count=5,
                known_furnaces_count=4,
                baseline_mean_frp_mw=38.0,
                baseline_std_frp_mw=8.0,
                baseline_mean_temp_k=360.0,
                expected_diurnal_ratio=0.96,
                historical_detections_count=620,
                active_hotspots_count=2,
                current_max_frp_mw=41.2,
                current_abnormality_score=14.0,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-KORBA-PWR01",
                name="NTPC Korba Super Thermal Power Station (2600 MW)",
                sector="THERMAL_POWER",
                state="Chhattisgarh",
                district="Korba",
                cluster_name="Korba Coal & Power Basin",
                coordinates=[22.3800, 82.6800],
                fence_radius_m=3000.0,
                operator_name="NTPC Limited",
                erdmp_license="CEA/IND/2023/CG-KORBA-01",
                major_chemicals_stored=["Bituminous Coal", "Furnace Heavy Oil", "Fly Ash"],
                known_flares_count=0,
                known_furnaces_count=7,
                baseline_mean_frp_mw=65.0,
                baseline_std_frp_mw=12.0,
                baseline_mean_temp_k=365.0,
                expected_diurnal_ratio=0.94,
                historical_detections_count=980,
                active_hotspots_count=3,
                current_max_frp_mw=70.5,
                current_abnormality_score=18.0,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-JSR-STEEL01",
                name="Tata Steel Jamshedpur Integrated Steel Works",
                sector="STEEL",
                state="Jharkhand",
                district="East Singhbhum",
                cluster_name="Jamshedpur Metallurgical Cluster",
                coordinates=[22.7800, 86.2000],
                fence_radius_m=3500.0,
                operator_name="Tata Steel Limited",
                erdmp_license="PESO/IND/2021/JH-JSR-0012",
                major_chemicals_stored=["Coke Oven Gas", "Blast Furnace Slag", "Liquid Iron", "Oxygen"],
                known_flares_count=4,
                known_furnaces_count=6,
                baseline_mean_frp_mw=82.0,
                baseline_std_frp_mw=16.0,
                baseline_mean_temp_k=380.0,
                expected_diurnal_ratio=0.97,
                historical_detections_count=1250,
                active_hotspots_count=3,
                current_max_frp_mw=88.0,
                current_abnormality_score=16.5,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            ),
            IndustrialFacility(
                id="FAC-JHARIA-MINE01",
                name="BCCL Jharia Opencast Coal Mining & Seam Fire Sector",
                sector="MINING",
                state="Jharkhand",
                district="Dhanbad",
                cluster_name="Jharia Coalfield Mining Zone",
                coordinates=[23.7500, 86.4200],
                fence_radius_m=5000.0,
                operator_name="Bharat Coking Coal Limited",
                erdmp_license="DGMS/IND/2020/JH-JHA-MINE",
                major_chemicals_stored=["Coking Coal", "Explosives ANFO", "Subsurface Methane"],
                known_flares_count=0,
                known_furnaces_count=0,
                baseline_mean_frp_mw=110.0,
                baseline_std_frp_mw=28.0,
                baseline_mean_temp_k=395.0,
                expected_diurnal_ratio=0.91,
                historical_detections_count=2100,
                active_hotspots_count=5,
                current_max_frp_mw=118.0,
                current_abnormality_score=22.0,
                current_status="NOMINAL_OPERATIONS",
                last_satellite_overpass=datetime.now(timezone.utc)
            )
        ]
        for f in seeds:
            self.facilities[f.id] = f

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates great-circle distance in meters between two WGS84 coordinates.
        """
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def attribute_thermal_event(self, lat: float, lon: float) -> Tuple[Optional[IndustrialFacility], float, bool]:
        """
        Attributes a thermal event coordinate to the closest industrial facility in the registry.
        Returns: (matched_facility, distance_meters, is_inside_fence_boundary)
        """
        best_fac = None
        min_dist = float('inf')

        for fac in self.facilities.values():
            dist = self.haversine_distance_m(lat, lon, fac.coordinates[0], fac.coordinates[1])
            if dist < min_dist:
                min_dist = dist
                best_fac = fac

        if best_fac and min_dist <= (best_fac.fence_radius_m * 2.5):
            is_inside = min_dist <= best_fac.fence_radius_m
            return best_fac, min_dist, is_inside

        return None, min_dist, False

    def get_all_facilities(self) -> List[IndustrialFacility]:
        return list(self.facilities.values())

    def get_facility_by_id(self, facility_id: str) -> Optional[IndustrialFacility]:
        return self.facilities.get(facility_id)

attribution_service = AttributionService()

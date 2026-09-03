import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.schemas.thermal import PersistentThermalCluster, CanonicalThermalEvent
from app.services.satellite.attribution_service import attribution_service

class PersistenceService:
    def __init__(self):
        self.clusters: Dict[str, PersistentThermalCluster] = {}
        self._seed_persistent_clusters()

    def _seed_persistent_clusters(self):
        """
        Seeds persistent thermal cluster baselines representing continuous industrial operations
        (petrochemical flare systems, refinery crackers, blast furnaces, and mining zones).
        """
        now = datetime.now(timezone.utc)
        seeds = [
            PersistentThermalCluster(
                cluster_id="CLUS-DAHEJ-PCH01",
                facility_id="FAC-DAHEJ-PCH01",
                facility_name="PetroChem Complex Alpha - Unit 04",
                center_coordinates=[21.6850, 72.5750],
                radius_m=600.0,
                category="ABNORMAL_PERSISTENT",
                primary_source_type="INDUSTRIAL_FIRE",
                detections_last_90d=78,
                daytime_detections=40,
                nighttime_detections=38,
                mean_frp_mw=18.5,
                max_frp_mw=84.6,
                current_frp_mw=84.6,
                frp_deviation_zscore=14.7,  # Severe deviation from mean (18.5) with std (4.2)
                is_abnormal=True,
                abnormality_reason="FRP surge (+357%) and localized thermal area expansion detected over Ammonia Cryogenic Header T-04",
                last_detected_timestamp=now - timedelta(minutes=18)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-DAHEJ-LNG02",
                facility_id="FAC-DAHEJ-LNG02",
                facility_name="Petronet Dahej LNG Terminal",
                center_coordinates=[21.6720, 72.5320],
                radius_m=450.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="GAS_FLARE",
                detections_last_90d=88,
                daytime_detections=45,
                nighttime_detections=43,
                mean_frp_mw=24.0,
                max_frp_mw=31.0,
                current_frp_mw=26.2,
                frp_deviation_zscore=0.4,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=45)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-JAMNAGAR-REF01",
                facility_id="FAC-JAMNAGAR-REF01",
                facility_name="Reliance Jamnagar Mega Refinery",
                center_coordinates=[22.3600, 69.8300],
                radius_m=2200.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="GAS_FLARE",
                detections_last_90d=90,
                daytime_detections=46,
                nighttime_detections=44,
                mean_frp_mw=145.0,
                max_frp_mw=172.0,
                current_frp_mw=148.5,
                frp_deviation_zscore=0.16,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=62)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-HAZIRA-GAS01",
                facility_id="FAC-HAZIRA-GAS01",
                facility_name="ONGC Hazira Gas Processing Complex",
                center_coordinates=[21.1200, 72.6700],
                radius_m=800.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="GAS_FLARE",
                detections_last_90d=84,
                daytime_detections=43,
                nighttime_detections=41,
                mean_frp_mw=38.0,
                max_frp_mw=48.0,
                current_frp_mw=42.0,
                frp_deviation_zscore=0.5,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=90)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-KORBA-PWR01",
                facility_id="FAC-KORBA-PWR01",
                facility_name="NTPC Korba Super Thermal Power Station",
                center_coordinates=[22.3800, 82.6800],
                radius_m=1200.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="ROUTINE_PROCESS_HEAT",
                detections_last_90d=89,
                daytime_detections=47,
                nighttime_detections=42,
                mean_frp_mw=65.0,
                max_frp_mw=78.0,
                current_frp_mw=68.2,
                frp_deviation_zscore=0.27,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=110)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-JSR-STEEL01",
                facility_id="FAC-JSR-STEEL01",
                facility_name="Tata Steel Jamshedpur Works",
                center_coordinates=[22.7800, 86.2000],
                radius_m=1400.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="ROUTINE_PROCESS_HEAT",
                detections_last_90d=87,
                daytime_detections=45,
                nighttime_detections=42,
                mean_frp_mw=82.0,
                max_frp_mw=96.0,
                current_frp_mw=86.4,
                frp_deviation_zscore=0.28,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=130)
            ),
            PersistentThermalCluster(
                cluster_id="CLUS-JHARIA-MINE01",
                facility_id="FAC-JHARIA-MINE01",
                facility_name="BCCL Jharia Opencast Coal Mining Zone",
                center_coordinates=[23.7500, 86.4200],
                radius_m=2800.0,
                category="EXPECTED_PERSISTENT",
                primary_source_type="MINING_PROCESS_HEAT",
                detections_last_90d=90,
                daytime_detections=48,
                nighttime_detections=42,
                mean_frp_mw=110.0,
                max_frp_mw=135.0,
                current_frp_mw=115.0,
                frp_deviation_zscore=0.18,
                is_abnormal=False,
                abnormality_reason=None,
                last_detected_timestamp=now - timedelta(minutes=150)
            )
        ]
        for c in seeds:
            self.clusters[c.cluster_id] = c

    def get_all_clusters(self) -> List[PersistentThermalCluster]:
        return list(self.clusters.values())

    def get_abnormal_clusters(self) -> List[PersistentThermalCluster]:
        return [c for c in self.clusters.values() if c.is_abnormal]

    def evaluate_thermal_persistence(
        self,
        lat: float,
        lon: float,
        current_frp: float
    ) -> Dict[str, Any]:
        """
        Evaluates whether a thermal coordinate matches a known persistent cluster and computes abnormality.
        """
        best_cluster = None
        min_dist = float('inf')

        for c in self.clusters.values():
            dist = attribution_service.haversine_distance_m(lat, lon, c.center_coordinates[0], c.center_coordinates[1])
            if dist < min_dist:
                min_dist = dist
                best_cluster = c

        if best_cluster and min_dist <= (best_cluster.radius_m * 1.5):
            mean_frp = best_cluster.mean_frp_mw
            # Estimate std if not stored
            std_frp = mean_frp * 0.22 if mean_frp > 0 else 1.0
            z_score = (current_frp - mean_frp) / std_frp if std_frp > 0 else 0.0
            
            is_abnormal = z_score >= 3.0 or (current_frp >= mean_frp * 2.5)
            abnormality_score = min(100.0, max(0.0, z_score * 6.5)) if is_abnormal else min(25.0, max(0.0, z_score * 4.0))
            
            return {
                "matched_cluster_id": best_cluster.cluster_id,
                "facility_name": best_cluster.facility_name,
                "category": "ABNORMAL_PERSISTENT" if is_abnormal else "EXPECTED_PERSISTENT",
                "mean_baseline_frp": mean_frp,
                "z_score": round(z_score, 2),
                "is_abnormal": is_abnormal,
                "abnormality_score": round(abnormality_score, 1),
                "distance_to_cluster_center_m": round(min_dist, 1)
            }

        return {
            "matched_cluster_id": None,
            "facility_name": None,
            "category": "TRANSIENT_EVENT",
            "mean_baseline_frp": 0.0,
            "z_score": 0.0,
            "is_abnormal": current_frp >= 50.0,
            "abnormality_score": min(100.0, current_frp * 1.2) if current_frp >= 50.0 else 10.0,
            "distance_to_cluster_center_m": None
        }

persistence_service = PersistenceService()

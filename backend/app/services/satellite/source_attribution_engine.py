import math
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.facility import IndustrialFacilityModel
from app.models.thermal_source import ThermalSourceModel, SourceFacilityCandidateModel

class SourceAttributionEngine:
    """
    Source-to-Facility Attribution Engine for SIH26162.
    Attributes a ThermalSourceObject to nearby IndustrialFacilities using:
    1. Exact polygon containment (GeoJSON Polygon/MultiPolygon ray-casting)
    2. Great-circle distance to facility centroid / fence radius
    3. Multi-candidate ranking (Top 3 candidates)
    4. Explainable attribution confidence scoring
    
    Attribution Statuses:
    - ATTRIBUTED_HIGH_CONFIDENCE (Inside perimeter or d < 300m)
    - ATTRIBUTED_MEDIUM_CONFIDENCE (d < 2.5 * fence_radius)
    - MULTIPLE_CANDIDATES (2+ facilities in close proximity)
    - UNATTRIBUTED (d > search threshold)
    """

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance in meters between two WGS84 coordinates."""
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def is_point_in_polygon(self, lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
        """
        Ray-casting algorithm for 2D Point-in-Polygon containment test.
        polygon_coords: list of [lon, lat] points forming a closed linear ring.
        """
        if not polygon_coords or len(polygon_coords) < 3:
            return False

        inside = False
        n = len(polygon_coords)
        p1_lon, p1_lat = polygon_coords[0]

        for i in range(1, n + 1):
            p2_lon, p2_lat = polygon_coords[i % n]
            if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
                if lon <= max(p1_lon, p2_lon):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                    if p1_lon == p2_lon or lon <= x_inters:
                        inside = not inside
            p1_lon, p1_lat = p2_lon, p2_lat

        return inside

    def attribute_source(
        self,
        source: ThermalSourceModel,
        db: Session,
        max_search_distance_m: float = 10000.0
    ) -> List[SourceFacilityCandidateModel]:
        """
        Evaluates all industrial facilities, ranks candidates by proximity and containment,
        and attaches candidate records to the database.
        """
        facilities = db.query(IndustrialFacilityModel).all()
        candidates_data = []

        for fac in facilities:
            dist_m = self.haversine_distance_m(source.centroid_lat, source.centroid_lon, fac.latitude, fac.longitude)
            if dist_m > max_search_distance_m:
                continue

            # Check polygon containment if boundary GeoJSON is present
            is_inside = False
            if fac.boundary_geojson and fac.boundary_geojson.get("type") == "Polygon":
                coords = fac.boundary_geojson.get("coordinates", [])
                if coords:
                    is_inside = self.is_point_in_polygon(source.centroid_lat, source.centroid_lon, coords[0])
            elif dist_m <= fac.fence_radius_m:
                is_inside = True

            # Calculate explainable confidence score
            if is_inside:
                confidence = 0.95
                evidence = f"Centroid located INSIDE unit perimeter polygon (dist: {dist_m:.0f}m)"
            elif dist_m <= fac.fence_radius_m * 1.5:
                confidence = round(0.85 - (dist_m / (fac.fence_radius_m * 3.0)), 2)
                evidence = f"Centroid within near-fence operational buffer ({dist_m:.0f}m from center)"
            elif dist_m <= fac.fence_radius_m * 3.0:
                confidence = round(0.60 - (dist_m / (fac.fence_radius_m * 6.0)), 2)
                evidence = f"Centroid within regional industrial corridor buffer ({dist_m:.0f}m)"
            else:
                confidence = round(max(0.1, 0.40 - (dist_m / max_search_distance_m)), 2)
                evidence = f"Peripheral industrial association ({dist_m:.0f}m)"

            candidates_data.append({
                "facility": fac,
                "distance_m": round(dist_m, 1),
                "is_inside": is_inside,
                "confidence": max(0.05, min(0.99, confidence)),
                "evidence": evidence
            })

        # Sort candidates: inside boundary first, then highest confidence / lowest distance
        candidates_data.sort(key=lambda c: (-int(c["is_inside"]), -c["confidence"], c["distance_m"]))

        # Clear old candidates for this source
        db.query(SourceFacilityCandidateModel).filter(
            SourceFacilityCandidateModel.source_id == source.source_id
        ).delete()

        created_candidates = []
        for rank, c in enumerate(candidates_data[:5], start=1):
            cand_model = SourceFacilityCandidateModel(
                source_id=source.source_id,
                facility_id=c["facility"].facility_id,
                facility_name=c["facility"].name,
                rank=rank,
                distance_m=c["distance_m"],
                is_inside_boundary=c["is_inside"],
                attribution_confidence=c["confidence"],
                evidence_summary=c["evidence"]
            )
            db.add(cand_model)
            created_candidates.append(cand_model)

        # Update primary source attribution fields
        if created_candidates:
            top = created_candidates[0]
            source.primary_attributed_facility_id = top.facility_id
            source.primary_attributed_facility_name = top.facility_name
            source.facility_distance_m = top.distance_m
            source.is_inside_facility_boundary = top.is_inside_boundary
            source.facility_attribution_confidence = top.attribution_confidence

            # Determine attribution status
            if top.is_inside_boundary or top.attribution_confidence >= 0.85:
                source.attribution_status = "ATTRIBUTED_HIGH_CONFIDENCE"
            elif len(created_candidates) > 1 and (created_candidates[1].distance_m - top.distance_m) < 400.0:
                source.attribution_status = "MULTIPLE_CANDIDATES"
            elif top.attribution_confidence >= 0.50:
                source.attribution_status = "ATTRIBUTED_MEDIUM_CONFIDENCE"
            else:
                source.attribution_status = "UNATTRIBUTED"
        else:
            source.primary_attributed_facility_id = None
            source.primary_attributed_facility_name = None
            source.facility_distance_m = None
            source.is_inside_facility_boundary = False
            source.facility_attribution_confidence = 0.0
            source.attribution_status = "UNATTRIBUTED"

        db.flush()
        return created_candidates

source_attribution_engine = SourceAttributionEngine()

import math
from typing import List, Optional, Tuple, Dict, Any, Set

try:
    import h3
    HAS_H3 = True
except ImportError:
    HAS_H3 = False

class SpatialIndexService:
    """
    Uber H3 spatial indexing and geospatial utility wrapper with pure-Python fallback.
    """

    def lat_lng_to_h3(self, lat: float, lon: float, resolution: int = 7) -> str:
        """
        Compute H3 hexagon spatial index for given latitude and longitude.
        Default resolution is 7 (~1.22 km edge length, optimal for FIRMS 375m/1km grouping).
        """
        if HAS_H3:
            try:
                if hasattr(h3, 'latlng_to_cell'):
                    return h3.latlng_to_cell(lat, lon, resolution)
                return h3.geo_to_h3(lat, lon, resolution)
            except Exception:
                pass
        
        # Deterministic Hexagonal Grid Fallback
        lat_q = round(lat * (10 ** (resolution - 3)))
        lon_q = round(lon * (10 ** (resolution - 3)))
        return f"h3_r{resolution}_{lat_q}_{lon_q}"

    def h3_to_lat_lng(self, h3_index: str) -> Optional[Tuple[float, float]]:
        """
        Compute centroid coordinate (lat, lon) for an H3 cell.
        """
        if HAS_H3:
            try:
                if hasattr(h3, 'cell_to_latlng'):
                    return h3.cell_to_latlng(h3_index)
                return h3.h3_to_geo(h3_index)
            except Exception:
                return None
        return None

    def k_ring(self, h3_index: str, k: int = 1) -> Set[str]:
        """
        Returns the H3 cell and all its k-ring neighboring cells.
        """
        if HAS_H3:
            try:
                if hasattr(h3, 'grid_disk'):
                    return set(h3.grid_disk(h3_index, k))
                return set(h3.k_ring(h3_index, k))
            except Exception:
                pass

        # Fallback pseudo-grid
        cells = {h3_index}
        if "_" in h3_index:
            parts = h3_index.split("_")
            if len(parts) == 4:
                prefix, r, lat_q_s, lon_q_s = parts
                lat_q = int(lat_q_s)
                lon_q = int(lon_q_s)
                for dlat in range(-k, k + 1):
                    for dlon in range(-k, k + 1):
                        cells.add(f"{prefix}_{r}_{lat_q + dlat}_{lon_q + dlon}")
        return cells

    def point_in_bbox(self, lat: float, lon: float, bbox: List[float]) -> bool:
        """
        Check if (lat, lon) falls within bounding box [min_lon, min_lat, max_lon, max_lat].
        """
        if len(bbox) != 4:
            return True
        min_lon, min_lat, max_lon, max_lat = bbox
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on the Earth's surface (in meters).
        """
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

spatial_index = SpatialIndexService()

# Backward compatibility functions
lat_lng_to_h3 = spatial_index.lat_lng_to_h3
h3_to_lat_lng = spatial_index.h3_to_lat_lng
point_in_bbox = spatial_index.point_in_bbox
haversine_distance_m = spatial_index.haversine_distance_m

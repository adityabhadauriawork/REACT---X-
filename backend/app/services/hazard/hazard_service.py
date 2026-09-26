import math
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from shapely.geometry import Polygon, MultiPolygon, Point, mapping
from shapely.affinity import rotate, translate
from app.schemas.hazard import ThreatZoneMetric, TimeSliceHazard, HazardSimulationResult
from app.services.weather.weather_service import weather_service

class HazardService:
    """
    Screening-level explainable hazard dispersion engine.
    NOTE: Prototype decision-support model for SIH workflow demonstration.
    Uses Gaussian plume / heavy gas screening equations with Pasquill-Gifford dispersion coefficients.
    """

    STABILITY_COEFFS = {
        "A": {"cy": 0.22, "dy": 0.90, "cz": 0.20, "dz": 1.00},
        "B": {"cy": 0.16, "dy": 0.90, "cz": 0.12, "dz": 1.00},
        "C": {"cy": 0.11, "dy": 0.90, "cz": 0.08, "dz": 0.92},
        "D": {"cy": 0.08, "dy": 0.90, "cz": 0.06, "dz": 0.88},
        "E": {"cy": 0.06, "dy": 0.90, "cz": 0.03, "dz": 0.82},
        "F": {"cy": 0.04, "dy": 0.90, "cz": 0.016, "dz": 0.78},
    }

    def _sigma_y(self, x: float, stability: str) -> float:
        coeffs = self.STABILITY_COEFFS.get(stability, self.STABILITY_COEFFS["D"])
        return max(1.5, coeffs["cy"] * (x ** coeffs["dy"]))

    def _sigma_z(self, x: float, stability: str) -> float:
        coeffs = self.STABILITY_COEFFS.get(stability, self.STABILITY_COEFFS["D"])
        return max(1.0, coeffs["cz"] * (x ** coeffs["dz"]))

    def _ppm_from_mg_m3(self, conc_mg_m3: float, mol_weight: float, temp_c: float, pressure_bar: float = 1.0) -> float:
        """Convert concentration in mg/m3 to ppm."""
        temp_k = temp_c + 273.15
        p_atm = pressure_bar * 0.986923
        return (conc_mg_m3 * 24.45 * (temp_k / 298.15)) / (mol_weight * max(0.1, p_atm))

    def _mg_m3_from_ppm(self, ppm: float, mol_weight: float, temp_c: float, pressure_bar: float = 1.0) -> float:
        """Convert ppm threshold to mg/m3."""
        temp_k = temp_c + 273.15
        p_atm = pressure_bar * 0.986923
        return (ppm * mol_weight * max(0.1, p_atm)) / (24.45 * (temp_k / 298.15))

    def calculate_plume_profile(
        self,
        q_kg_s: float,
        u_m_s: float,
        stability: str,
        threshold_mg_m3: float,
        max_dist_m: float = 3000.0,
        time_limit_sec: Optional[float] = None
    ) -> Tuple[List[float], List[float], float, float]:
        """
        Calculate downwind (x) and half-width (y) coordinates where concentration == threshold.
        Returns: (x_pts, y_half_width_pts, max_reach_m, max_width_m)
        """
        q_mg_s = q_kg_s * 1e6
        x_values = np.linspace(2.0, max_dist_m, 200)
        valid_x = []
        valid_y = []

        eff_u = max(0.5, u_m_s)
        time_max_reach = (eff_u * time_limit_sec) if time_limit_sec is not None else max_dist_m

        for x in x_values:
            if x > time_max_reach:
                break
            sy = self._sigma_y(x, stability)
            sz = self._sigma_z(x, stability)
            centerline_c = q_mg_s / (math.pi * eff_u * sy * sz)
            
            if centerline_c >= threshold_mg_m3:
                ratio = threshold_mg_m3 / centerline_c
                y_half = sy * math.sqrt(max(0.0, 2.0 * math.log(1.0 / ratio)))
                valid_x.append(float(x))
                valid_y.append(float(y_half))
            elif len(valid_x) > 0:
                # Plume concentration dropped below threshold
                break

        if not valid_x:
            # Minimal safety sphere around source
            min_r = min(15.0, time_max_reach if time_limit_sec else 15.0)
            return [2.0, min_r], [min_r / 2.0, 0.0], min_r, min_r

        max_reach = max(valid_x)
        max_width = 2.0 * max(valid_y) if valid_y else 5.0
        return valid_x, valid_y, max_reach, max_width

    def _generate_geographic_polygon(
        self,
        center_lat: float,
        center_lon: float,
        x_pts: List[float],
        y_pts: List[float],
        wind_direction_deg: float,
        time_sec: Optional[int] = None
    ) -> Polygon:
        """
        Construct a smooth 2D polygon in downwind cartesian coordinates and rotate/project to (lat, lon).
        Wind direction is the direction the wind is blowing FROM; plume travels TOWARDS (wind_dir + 180)%360 or wind angle.
        In meteorological standard: wind direction angle $\theta$ is where wind is blowing FROM.
        Plume travels in direction: azimuth = (wind_direction_deg + 180) % 360 or if wind vector is direction OF wind, then azimuth = wind_direction_deg.
        We define wind_direction_deg as the travel vector (direction cloud is blown towards, e.g. 45° = North-East).
        """
        travel_azimuth_deg = wind_direction_deg % 360.0
        rad = math.radians(travel_azimuth_deg)

        # Build local Cartesian points in meters (x along plume travel axis, y perpendicular)
        cartesian_points = []

        # Source puff circular base
        initial_radius = min(8.0, x_pts[0])
        for angle in np.linspace(-math.pi / 2, math.pi / 2, 8):
            cartesian_points.append((-initial_radius * math.cos(angle), initial_radius * math.sin(angle)))

        # Top half of plume envelope
        for x, y in zip(x_pts, y_pts):
            cartesian_points.append((x, y))

        # Tip rounded cap
        if x_pts and y_pts:
            tip_x = x_pts[-1]
            tip_y = max(1.0, y_pts[-1])
            cartesian_points.append((tip_x + tip_y * 0.4, 0.0))

        # Bottom half of plume envelope (reversed)
        for x, y in zip(reversed(x_pts), reversed(y_pts)):
            cartesian_points.append((x, -y))

        # Close polygon
        if cartesian_points:
            cartesian_points.append(cartesian_points[0])

        # Convert local cartesian (x_downwind, y_crosswind) to lat/lon
        # Local transformation:
        # x_north = x * cos(rad) - y * sin(rad)
        # x_east  = x * sin(rad) + y * cos(rad)
        geo_coords = []
        lat_scale = 111132.0  # meters per degree latitude
        lon_scale = 111132.0 * math.cos(math.radians(center_lat))

        for x_m, y_m in cartesian_points:
            x_north = x_m * math.cos(rad) - y_m * math.sin(rad)
            x_east = x_m * math.sin(rad) + y_m * math.cos(rad)

            pt_lat = center_lat + (x_north / lat_scale)
            pt_lon = center_lon + (x_east / lon_scale)
            geo_coords.append((pt_lon, pt_lat))  # GeoJSON expects (lon, lat)

        poly = Polygon(geo_coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly

    def simulate_scenario(
        self,
        scenario_data: Dict[str, Any],
        chemical_data: Dict[str, Any],
        source_coords: List[float],
        time_steps: List[int] = [0, 30, 60, 120]
    ) -> HazardSimulationResult:
        """
        Run the explainable screening dispersion simulation.
        Generates Toxic/Flammability/Threat Zones and time-progression GeoJSON polygons.
        """
        q_kg_s = float(scenario_data.get("release_rate_kg_s", 15.0))
        wind_kmh = float(scenario_data.get("wind_speed_kmh", 8.0))
        wind_u_m_s = max(0.5, wind_kmh / 3.6)
        wind_deg = float(scenario_data.get("wind_direction_deg", 45.0))
        stability = str(scenario_data.get("atmospheric_stability", "D"))
        temp_c = float(scenario_data.get("ambient_temp_c", 32.0))
        pressure_bar = float(scenario_data.get("operating_pressure_bar", 4.5))
        incident_type = scenario_data.get("incident_type", "PIPELINE_LEAK")
        mw = chemical_data.get("molecular_weight", 17.03)

        # Determine threshold levels based on incident type and chemical properties
        is_explosion = incident_type == "FIRE_EXPLOSION"

        if is_explosion:
            # Thermal / Overpressure zones
            red_label = "Lethal Thermal Radiation (10 kW/m² / 5 psi)"
            orange_label = "Second-Degree Burn Zone (5 kW/m² / 2 psi)"
            yellow_label = "Cautionary Exposure (2 kW/m² / 1 psi)"

            # Scaling distances for blast / fire based on TNT/release mass equivalence
            red_reach = max(20.0, 15.0 * (q_kg_s ** 0.45))
            orange_reach = max(40.0, 30.0 * (q_kg_s ** 0.45))
            yellow_reach = max(80.0, 65.0 * (q_kg_s ** 0.45))

            # Virtual thresholds for calculation
            th_red = 1000.0
            th_orange = 500.0
            th_yellow = 200.0
        else:
            # Toxic or Flammable Dispersion
            erpg_3 = chemical_data.get("erpg_3_ppm") or (chemical_data.get("lfl_percent", 2.0) * 10000.0 * 0.6)
            erpg_2 = chemical_data.get("erpg_2_ppm") or (chemical_data.get("lfl_percent", 2.0) * 10000.0 * 0.2)
            erpg_1 = chemical_data.get("erpg_1_ppm") or (chemical_data.get("lfl_percent", 2.0) * 10000.0 * 0.1)

            red_label = f"ERPG-3 / High Lethality ({erpg_3:.1f} ppm)"
            orange_label = f"ERPG-2 / Irreversible Injury ({erpg_2:.1f} ppm)"
            yellow_label = f"ERPG-1 / Mild Irritation ({erpg_1:.1f} ppm)"

            th_red = self._mg_m3_from_ppm(erpg_3, mw, temp_c, 1.0)
            th_orange = self._mg_m3_from_ppm(erpg_2, mw, temp_c, 1.0)
            th_yellow = self._mg_m3_from_ppm(erpg_1, mw, temp_c, 1.0)

        # Compute steady-state profiles for metrics
        x_red, y_red, reach_red, w_red = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_red)
        x_org, y_org, reach_org, w_org = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_orange)
        x_yel, y_yel, reach_yel, w_yel = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_yellow)

        # Generate polygons for each time step
        time_slice_hazards = []
        center_lat, center_lon = source_coords[0], source_coords[1]

        for t_sec in time_steps:
            eff_t = None if t_sec >= 120 else max(5.0, float(t_sec))

            # Red Zone
            xr_t, yr_t, mr_red, _ = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_red, time_limit_sec=eff_t)
            poly_red = self._generate_geographic_polygon(center_lat, center_lon, xr_t, yr_t, wind_deg, t_sec)

            # Orange Zone
            xo_t, yo_t, mr_org, _ = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_orange, time_limit_sec=eff_t)
            poly_org = self._generate_geographic_polygon(center_lat, center_lon, xo_t, yo_t, wind_deg, t_sec)

            # Yellow Zone
            xy_t, yy_t, mr_yel, _ = self.calculate_plume_profile(q_kg_s, wind_u_m_s, stability, th_yellow, time_limit_sec=eff_t)
            poly_yel = self._generate_geographic_polygon(center_lat, center_lon, xy_t, yy_t, wind_deg, t_sec)

            # Build GeoJSON feature collection for this time step
            features = [
                {
                    "type": "Feature",
                    "id": f"zone-yellow-t{t_sec}",
                    "geometry": mapping(poly_yel),
                    "properties": {
                        "zone_id": "YELLOW_ZONE_CAUTION",
                        "name": "Yellow Threat Zone (Caution / Mild Effect)",
                        "threshold_label": yellow_label,
                        "color": "#eab308",
                        "stroke": "#ca8a04",
                        "opacity": 0.25,
                        "fillOpacity": 0.20,
                        "max_distance_m": round(mr_yel, 1),
                        "time_step_sec": t_sec
                    }
                },
                {
                    "type": "Feature",
                    "id": f"zone-orange-t{t_sec}",
                    "geometry": mapping(poly_org),
                    "properties": {
                        "zone_id": "ORANGE_ZONE_INJURY",
                        "name": "Orange Threat Zone (Severe Injury / Impairment)",
                        "threshold_label": orange_label,
                        "color": "#f97316",
                        "stroke": "#ea580c",
                        "opacity": 0.40,
                        "fillOpacity": 0.35,
                        "max_distance_m": round(mr_org, 1),
                        "time_step_sec": t_sec
                    }
                },
                {
                    "type": "Feature",
                    "id": f"zone-red-t{t_sec}",
                    "geometry": mapping(poly_red),
                    "properties": {
                        "zone_id": "RED_ZONE_LETHAL",
                        "name": "Red Threat Zone (Lethal / Severe Destruction)",
                        "threshold_label": red_label,
                        "color": "#ef4444",
                        "stroke": "#b91c1c",
                        "opacity": 0.60,
                        "fillOpacity": 0.50,
                        "max_distance_m": round(mr_red, 1),
                        "time_step_sec": t_sec
                    }
                }
            ]

            geojson_doc = {
                "type": "FeatureCollection",
                "features": features
            }

            active_metrics = [
                ThreatZoneMetric(
                    zone_type="RED_ZONE_LETHAL",
                    name="Red Threat Zone",
                    threshold_label=red_label,
                    concentration_threshold_ppm=chemical_data.get("erpg_3_ppm"),
                    max_downwind_distance_m=round(mr_red, 1),
                    max_crosswind_width_m=round(w_red * (mr_red / max(1.0, reach_red)), 1),
                    area_sq_m=round(poly_red.area * 1e10, 1),  # approx sq m
                    color="#ef4444",
                    opacity=0.55
                ),
                ThreatZoneMetric(
                    zone_type="ORANGE_ZONE_INJURY",
                    name="Orange Threat Zone",
                    threshold_label=orange_label,
                    concentration_threshold_ppm=chemical_data.get("erpg_2_ppm"),
                    max_downwind_distance_m=round(mr_org, 1),
                    max_crosswind_width_m=round(w_org * (mr_org / max(1.0, reach_org)), 1),
                    area_sq_m=round(poly_org.area * 1e10, 1),
                    color="#f97316",
                    opacity=0.40
                ),
                ThreatZoneMetric(
                    zone_type="YELLOW_ZONE_CAUTION",
                    name="Yellow Threat Zone",
                    threshold_label=yellow_label,
                    concentration_threshold_ppm=chemical_data.get("erpg_1_ppm"),
                    max_downwind_distance_m=round(mr_yel, 1),
                    max_crosswind_width_m=round(w_yel * (mr_yel / max(1.0, reach_yel)), 1),
                    area_sq_m=round(poly_yel.area * 1e10, 1),
                    color="#eab308",
                    opacity=0.25
                )
            ]

            time_slice_hazards.append(
                TimeSliceHazard(
                    time_step_sec=t_sec,
                    time_label=f"T+{t_sec}s",
                    plume_front_distance_m=round(mr_yel, 1),
                    geojson=geojson_doc,
                    active_threat_zones=active_metrics
                )
            )

        # Summary steady-state zones (at max time)
        summary_zones = time_slice_hazards[-1].active_threat_zones

        weather_mode = scenario_data.get("weather_mode", "LIVE")
        weather_source = scenario_data.get("weather_source", "Open-Meteo" if weather_mode == "LIVE" else "Scenario Override")

        return HazardSimulationResult(
            scenario_id=scenario_data.get("id"),
            incident_type=incident_type,
            chemical_id=chemical_data.get("id", "CHEM-UNKNOWN"),
            chemical_name=chemical_data.get("name", "Unknown Chemical"),
            source_asset_id=scenario_data.get("asset_id", "T-04"),
            source_coordinates=source_coords,
            wind_speed_kmh=wind_kmh,
            wind_direction_deg=wind_deg,
            wind_direction_cardinal=weather_service.deg_to_cardinal(wind_deg),
            atmospheric_stability=stability,
            ambient_temp_c=temp_c,
            weather_mode=weather_mode,
            weather_source=weather_source,
            effective_release_rate_kg_s=q_kg_s,
            time_steps=time_slice_hazards,
            current_time_step_sec=120,
            current_geojson=time_slice_hazards[-1].geojson,
            summary_zones=summary_zones,
            model_metadata={
                "model_type": "Gaussian Screening Plume Dispersion Approximation",
                "stability_class": stability,
                "ambient_temp_c": temp_c,
                "roughness_length_m": 0.5,
                "advection_speed_m_s": round(wind_u_m_s, 2),
                "is_certified_aloha": False,
                "purpose": "REACT-X Decision-Support Screening Workflow"
            }
        )

hazard_service = HazardService()

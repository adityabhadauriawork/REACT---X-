import math
import networkx as nx
from typing import Dict, Any, List, Tuple, Optional
from shapely.geometry import shape, Point, LineString
from sqlalchemy.orm import Session
from app.models.plant import RoadModel, AssemblyPointModel, GateModel, AssetModel
from app.schemas.evacuation import (
    EvacuationRouteResult, RouteStep, EvacuationPlanResponse,
    RouteScoreBreakdown, CandidateRouteSummary
)
from app.schemas.hazard import HazardSimulationResult
from app.schemas.impact import ImpactAnalysisResult

class EvacuationService:
    @staticmethod
    def _haversine_distance_m(coord1: List[float], coord2: List[float]) -> float:
        """Calculate real ground distance between two (lat, lon) pairs in meters."""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        R = 6371000.0  # Earth radius in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    def _calculate_linestring_length_m(self, coords: List[List[float]]) -> float:
        total = 0.0
        for i in range(len(coords) - 1):
            total += self._haversine_distance_m(coords[i], coords[i + 1])
        return max(1.0, total)

    @staticmethod
    def _calculate_bearing_deg(coord1: List[float], coord2: List[float]) -> float:
        """Calculate compass bearing (0-360 degrees) from coord1 to coord2."""
        lat1 = math.radians(coord1[0])
        lat2 = math.radians(coord2[0])
        dlon = math.radians(coord2[1] - coord1[1])
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0

    def generate_evacuation_plan(
        self,
        db: Session,
        simulation_result: HazardSimulationResult,
        impact_result: ImpactAnalysisResult,
        origin_coords: Optional[List[float]] = None,
        origin_name: Optional[str] = None
    ) -> EvacuationPlanResponse:
        """
        Dynamically evaluate road network against the CURRENT hazard geometry,
        score all candidate assembly points and perimeter gates based on safety,
        crosswind/upwind angular clearance, and path distance, and generate an explainable plan.
        """
        roads = db.query(RoadModel).all()
        assembly_points = db.query(AssemblyPointModel).all()
        gates = db.query(GateModel).all()

        if not roads or not assembly_points or not gates:
            from app.services.site.site_service import site_service
            site_service.load_seed_data_if_empty(db)
            roads = db.query(RoadModel).all()
            assembly_points = db.query(AssemblyPointModel).all()
            gates = db.query(GateModel).all()

        blocked_road_ids = {br.id for br in impact_result.blocked_roads} if impact_result and impact_result.blocked_roads else set()
        safe_ap_ids = {ap.id for ap in impact_result.assembly_points if ap.status == "SAFE"} if impact_result and impact_result.assembly_points else set()

        # Extract hazard polygons for spatial intersection checks
        hazard_step = simulation_result.time_steps[-1] if simulation_result.time_steps else None
        red_poly = None
        orange_poly = None
        yellow_poly = None

        if hazard_step and hazard_step.geojson:
            for feat in hazard_step.geojson.get("features", []):
                zid = feat["properties"].get("zone_id")
                if zid == "RED_ZONE_LETHAL":
                    red_poly = shape(feat["geometry"])
                elif zid == "ORANGE_ZONE_INJURY":
                    orange_poly = shape(feat["geometry"])
                elif zid == "YELLOW_ZONE_CAUTION":
                    yellow_poly = shape(feat["geometry"])

        # Determine Plume Travel Direction
        # Wind direction is where wind comes from; plume travels downwind = (wind_deg + 180) % 360
        wind_from_deg = simulation_result.wind_direction_deg
        plume_travel_deg = (wind_from_deg + 180.0) % 360.0
        src_coords = simulation_result.source_coordinates or [21.6850, 72.5750]

        if not origin_coords:
            origin_coords = src_coords
            origin_name = f"Incident Origin ({simulation_result.source_asset_id} Vicinity)"
        else:
            origin_name = origin_name or "Affected Sector Zone"

        # 1. Build Passable Dynamic NetworkX Graph
        G_all = nx.Graph()
        G_safe = nx.Graph()
        node_coords: Dict[str, List[float]] = {}

        for r in roads:
            coords = r.coordinates_json
            if not coords or len(coords) < 2:
                continue
            from_node = r.from_node
            to_node = r.to_node
            node_coords[from_node] = coords[0]
            node_coords[to_node] = coords[-1]

            road_len = self._calculate_linestring_length_m(coords)
            line_pts = [(p[1], p[0]) for p in coords]  # (lon, lat) for shapely
            road_geom = LineString(line_pts)

            # Check exact geometric intersection with current hazard polygons
            intersects_red = red_poly.intersects(road_geom) if red_poly else False
            intersects_orange = orange_poly.intersects(road_geom) if orange_poly else False
            intersects_yellow = yellow_poly.intersects(road_geom) if yellow_poly else False

            is_blocked = (r.id in blocked_road_ids) or intersects_red or intersects_orange

            if is_blocked:
                edge_weight = 999999.0
                is_passable = False
                road_status = "BLOCKED"
            elif intersects_yellow:
                edge_weight = road_len * 3.5  # Caution speed reduction
                is_passable = True
                road_status = "CAUTION"
            else:
                edge_weight = road_len
                is_passable = True
                road_status = "CLEAR"

            edge_attr = {
                "road_id": r.id,
                "road_name": r.name,
                "weight": edge_weight,
                "actual_length": road_len,
                "passable": is_passable,
                "status": road_status,
                "coordinates": coords
            }

            G_all.add_edge(from_node, to_node, **edge_attr)
            if is_passable:
                G_safe.add_edge(from_node, to_node, **edge_attr)

        # Fallback synthesis if roads / node_coords is empty
        if not node_coords:
            node_coords["N-01"] = [src_coords[0] + 0.003, src_coords[1] - 0.004]
            node_coords["N-02"] = [src_coords[0] + 0.003, src_coords[1] + 0.004]
            node_coords["N-03"] = [src_coords[0] - 0.003, src_coords[1] - 0.004]
            node_coords["N-04"] = [src_coords[0] - 0.003, src_coords[1] + 0.004]
            G_all.add_edge("N-01", "N-02", weight=700.0, actual_length=700.0, passable=True, status="CLEAR")
            G_all.add_edge("N-03", "N-04", weight=700.0, actual_length=700.0, passable=True, status="CLEAR")
            G_safe.add_edge("N-01", "N-02", weight=700.0, actual_length=700.0, passable=True, status="CLEAR")
            G_safe.add_edge("N-03", "N-04", weight=700.0, actual_length=700.0, passable=True, status="CLEAR")

        # 2. Find Closest Accessible Node to Origin
        closest_origin_node = min(
            node_coords.keys(),
            key=lambda n: self._haversine_distance_m(origin_coords, node_coords[n])
        )

        # Map Assembly Points and Gates to nearest nodes
        ap_nearest_node: Dict[str, str] = {}
        for ap in assembly_points:
            ap_nearest_node[ap.id] = min(
                node_coords.keys(),
                key=lambda n: self._haversine_distance_m([ap.lat, ap.lon], node_coords[n])
            )

        gate_nearest_node: Dict[str, str] = {}
        for g in gates:
            gate_nearest_node[g.id] = min(
                node_coords.keys(),
                key=lambda n: self._haversine_distance_m([g.lat, g.lon], node_coords[n])
            )

        # 3. Exhaustively Evaluate All Candidate Assembly Points & Gates
        candidate_evaluations: List[Dict[str, Any]] = []

        for ap in assembly_points:
            ap_coord = [ap.lat, ap.lon]
            ap_pt = Point(ap.lon, ap.lat)

            # Check if AP itself is inside hazard zones
            in_red = red_poly.contains(ap_pt) if red_poly else False
            in_orange = orange_poly.contains(ap_pt) if orange_poly else False
            in_yellow = yellow_poly.contains(ap_pt) if yellow_poly else False

            # Calculate bearing from leak source to Assembly Point
            bearing_to_ap = self._calculate_bearing_deg(src_coords, ap_coord)
            angular_diff_to_plume = abs((bearing_to_ap - plume_travel_deg + 180) % 360 - 180)
            
            # Upwind / crosswind classification:
            # If angular_diff_to_plume > 90°, target is upwind of leak!
            # If angular_diff_to_plume in [45°, 90°], target is crosswind.
            # If angular_diff_to_plume < 45°, target is directly downwind (danger zone)!
            is_upwind = angular_diff_to_plume >= 80.0
            is_downwind = angular_diff_to_plume < 45.0

            # Find matching closest open gate
            associated_gate = min(
                [g for g in gates if g.status == "OPEN"] or gates,
                key=lambda g: self._haversine_distance_m([g.lat, g.lon], ap_coord)
            )

            target_ap_node = ap_nearest_node[ap.id]

            # Pathfinding evaluation on passable graph
            has_road_path = False
            path_nodes = []
            path_distance_m = 0.0
            path_intersects_caution = False

            if closest_origin_node in G_safe and target_ap_node in G_safe:
                try:
                    path_nodes = nx.shortest_path(G_safe, source=closest_origin_node, target=target_ap_node, weight="weight")
                    has_road_path = True
                    
                    # Calculate actual distance
                    dist_to_first = self._haversine_distance_m(origin_coords, node_coords[closest_origin_node])
                    path_distance_m += dist_to_first
                    
                    for i in range(len(path_nodes) - 1):
                        u, v = path_nodes[i], path_nodes[i + 1]
                        ed = G_safe.get_edge_data(u, v)
                        path_distance_m += ed.get("actual_length", 50.0)
                        if ed.get("status") == "CAUTION":
                            path_intersects_caution = True
                            
                    dist_to_ap = self._haversine_distance_m(node_coords[target_ap_node], ap_coord)
                    path_distance_m += dist_to_ap
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    has_road_path = False

            # If no direct internal road path, evaluate peripheral clearance corridor
            if not has_road_path:
                # Egress using outer perimeter roads
                p_dist = (
                    self._haversine_distance_m(origin_coords, node_coords[closest_origin_node]) +
                    self._haversine_distance_m(node_coords[closest_origin_node], [node_coords[closest_origin_node][0], ap.lon]) +
                    self._haversine_distance_m([node_coords[closest_origin_node][0], ap.lon], ap_coord)
                )
                path_distance_m = p_dist

            # Multi-Factor Scoring
            # 1. Safety Score (0.0 to 1.0)
            if in_red or in_orange:
                safety_score = 0.05
                rejection_reason = f"Assembly Point inside toxic hazard envelope ({'Red Lethal Zone' if in_red else 'Orange Severe Zone'})"
                route_status = "REJECTED"
            elif is_downwind and not is_upwind:
                safety_score = 0.25
                rejection_reason = f"Downwind of toxic plume ({angular_diff_to_plume:.0f}° from plume axis); high vapor inhalation hazard"
                route_status = "REJECTED" if in_yellow else "CAUTION"
            elif in_yellow or path_intersects_caution:
                safety_score = 0.65
                rejection_reason = "Route/Muster intersects Yellow caution buffer"
                route_status = "CAUTION"
            elif not has_road_path:
                safety_score = 0.70
                rejection_reason = "Internal access roads severed; requires outer peripheral detour"
                route_status = "DIVERTED"
            else:
                # Upwind / Crosswind with clear passable road
                safety_score = 0.95 if is_upwind else 0.85
                rejection_reason = None
                route_status = "CLEAR"

            # 2. Distance Score (0.0 to 1.0)
            distance_score = max(0.1, round(1.0 - (path_distance_m / 1600.0), 3))

            # 3. Exposure Penalty (0.0 to 1.0)
            exposure_penalty = 0.0
            if in_red: exposure_penalty += 0.90
            elif in_orange: exposure_penalty += 0.70
            elif in_yellow: exposure_penalty += 0.35
            if is_downwind: exposure_penalty += 0.40
            if path_intersects_caution: exposure_penalty += 0.15
            exposure_penalty = min(1.0, round(exposure_penalty, 3))

            # 4. Composite Score
            composite_score = round(
                (0.60 * safety_score) + (0.40 * distance_score) - (0.50 * exposure_penalty),
                3
            )
            composite_score = max(0.01, min(1.0, composite_score))

            est_time_min = round(path_distance_m / 72.0, 1)

            candidate_evaluations.append({
                "candidate_id": f"ROUTE-{ap.id}",
                "ap": ap,
                "gate": associated_gate,
                "has_road_path": has_road_path,
                "path_nodes": path_nodes,
                "distance_m": round(path_distance_m, 1),
                "estimated_time_min": est_time_min,
                "safety_score": safety_score,
                "distance_score": distance_score,
                "exposure_penalty": exposure_penalty,
                "composite_score": composite_score,
                "is_upwind": is_upwind,
                "angular_clearance_deg": round(angular_diff_to_plume, 1),
                "route_status": route_status,
                "rejection_reason": rejection_reason,
                "in_hazard": in_red or in_orange or in_yellow
            })

        # 4. Sort Candidates by Composite Score
        candidate_evaluations.sort(key=lambda c: c["composite_score"], reverse=True)

        best_cand = candidate_evaluations[0]
        chosen_ap = best_cand["ap"]
        chosen_gate = best_cand["gate"]

        # Build turn-by-turn steps and GeoJSON coordinates for best candidate
        route_coords = [origin_coords]
        steps: List[RouteStep] = []
        step_idx = 1
        total_dist_m = 0.0

        if best_cand["has_road_path"] and len(best_cand["path_nodes"]) >= 2:
            path_nodes = best_cand["path_nodes"]
            dist_to_first = self._haversine_distance_m(origin_coords, node_coords[path_nodes[0]])
            steps.append(
                RouteStep(
                    step_number=step_idx,
                    instruction=f"Exit work area immediately crosswind ({best_cand['angular_clearance_deg']:.0f}° from plume) towards {path_nodes[0]} access junction",
                    road_name="Local Asset Access Lane",
                    distance_m=round(dist_to_first, 1),
                    coordinates=[origin_coords, node_coords[path_nodes[0]]]
                )
            )
            total_dist_m += dist_to_first
            route_coords.append(node_coords[path_nodes[0]])
            step_idx += 1

            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i + 1]
                edge_data = G_safe.get_edge_data(u, v)
                seg_coords = edge_data.get("coordinates", [node_coords[u], node_coords[v]])
                seg_len = edge_data.get("actual_length", 50.0)

                if self._haversine_distance_m(seg_coords[0], node_coords[u]) > self._haversine_distance_m(seg_coords[-1], node_coords[u]):
                    seg_coords = list(reversed(seg_coords))

                steps.append(
                    RouteStep(
                        step_number=step_idx,
                        instruction=f"Proceed along {edge_data.get('road_name')} towards {v} ({edge_data.get('status')} Corridor)",
                        road_name=edge_data.get("road_name", "Perimeter Road"),
                        distance_m=round(seg_len, 1),
                        coordinates=seg_coords
                    )
                )
                total_dist_m += seg_len
                for c in seg_coords[1:]:
                    route_coords.append(c)
                step_idx += 1

            dist_to_ap = self._haversine_distance_m(node_coords[path_nodes[-1]], [chosen_ap.lat, chosen_ap.lon])
            steps.append(
                RouteStep(
                    step_number=step_idx,
                    instruction=f"Arrive at {chosen_ap.name} for headcount verification and emergency triage",
                    road_name="Assembly Point Staging Zone",
                    distance_m=round(dist_to_ap, 1),
                    coordinates=[node_coords[path_nodes[-1]], [chosen_ap.lat, chosen_ap.lon]]
                )
            )
            total_dist_m += dist_to_ap
            route_coords.append([chosen_ap.lat, chosen_ap.lon])
        else:
            # Peripheral detour
            p1 = origin_coords
            p2 = node_coords[closest_origin_node]
            p3 = [node_coords[closest_origin_node][0], chosen_ap.lon]
            p4 = [chosen_ap.lat, chosen_ap.lon]
            
            route_coords = [p1, p2, p3, p4]
            d1 = self._haversine_distance_m(p1, p2)
            d2 = self._haversine_distance_m(p2, p3)
            d3 = self._haversine_distance_m(p3, p4)
            total_dist_m = d1 + d2 + d3

            steps = [
                RouteStep(
                    step_number=1,
                    instruction=f"Move crosswind ({best_cand['angular_clearance_deg']:.0f}° angle) away from release point to perimeter lane",
                    road_name="Emergency Crosswind Egress Lane",
                    distance_m=round(d1, 1),
                    coordinates=[p1, p2]
                ),
                RouteStep(
                    step_number=2,
                    instruction=f"Proceed along outer safety corridor clear of the downwind hazard plume",
                    road_name="Outer Perimeter Clearance Corridor",
                    distance_m=round(d2, 1),
                    coordinates=[p2, p3]
                ),
                RouteStep(
                    step_number=3,
                    instruction=f"Muster at {chosen_ap.name} for head-count verification and medical triage",
                    road_name="Assembly Point Staging Zone",
                    distance_m=round(d3, 1),
                    coordinates=[p3, p4]
                )
            ]

        est_time_min = round(total_dist_m / 72.0, 1)

        # Build GeoJSON
        route_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[p[1], p[0]] for p in route_coords]
                    },
                    "properties": {
                        "name": f"Recommended Evacuation Route to {chosen_ap.name}",
                        "status": best_cand["route_status"],
                        "color": "#10b981",
                        "distance_m": round(total_dist_m, 1),
                        "time_min": est_time_min,
                        "safety_score": best_cand["safety_score"],
                        "composite_score": best_cand["composite_score"]
                    }
                }
            ]
        }

        # Build Candidate Route Summaries
        candidate_summaries: List[CandidateRouteSummary] = []
        rejected_summaries: List[CandidateRouteSummary] = []

        for idx, cand in enumerate(candidate_evaluations):
            is_winner = (idx == 0)
            is_backup = (idx == 1 and cand["composite_score"] > 0.40)
            
            c_status = "SELECTED" if is_winner else ("VIABLE_BACKUP" if is_backup else "REJECTED")
            rej_reason = None
            if not is_winner:
                if cand["rejection_reason"]:
                    rej_reason = cand["rejection_reason"]
                elif cand["distance_m"] > best_cand["distance_m"]:
                    extra_dist = round(cand["distance_m"] - best_cand["distance_m"], 0)
                    extra_min = round((cand["distance_m"] - best_cand["distance_m"]) / 72.0, 1)
                    rej_reason = f"Longer route (+{extra_dist}m, +{extra_min} min delay) with lower clearance score ({cand['composite_score']:.2f} vs {best_cand['composite_score']:.2f})"
                else:
                    rej_reason = f"Lower safety/composite score ({cand['composite_score']:.2f} vs {best_cand['composite_score']:.2f})"

            summary_item = CandidateRouteSummary(
                candidate_id=cand["candidate_id"],
                target_assembly_point_id=cand["ap"].id,
                target_assembly_point_name=cand["ap"].name,
                target_gate_id=cand["gate"].id,
                target_gate_name=cand["gate"].name,
                total_distance_m=cand["distance_m"],
                estimated_evac_time_min=cand["estimated_time_min"],
                route_status=c_status,
                safety_score=cand["safety_score"],
                distance_score=cand["distance_score"],
                exposure_penalty=cand["exposure_penalty"],
                composite_score=cand["composite_score"],
                is_upwind=cand["is_upwind"],
                angular_clearance_deg=cand["angular_clearance_deg"],
                rejection_reason=rej_reason
            )

            candidate_summaries.append(summary_item)
            if not is_winner:
                rejected_summaries.append(summary_item)

        # Selection Rationale
        upwind_str = "Upwind/Crosswind" if best_cand["is_upwind"] else "Crosswind"
        selection_reason = (
            f"Selected as optimal {upwind_str} egress corridor ({best_cand['angular_clearance_deg']:.0f}° clearance from plume axis) "
            f"providing shortest uncompromised route to {chosen_ap.name} (Safety Score: {best_cand['safety_score']:.2f}, Composite Score: {best_cand['composite_score']:.2f})."
        )

        score_breakdown = RouteScoreBreakdown(
            safety_score=best_cand["safety_score"],
            distance_score=best_cand["distance_score"],
            exposure_penalty=best_cand["exposure_penalty"],
            composite_score=best_cand["composite_score"],
            selection_reason=selection_reason
        )

        avoided_roads = [br.name for br in impact_result.blocked_roads]
        caution_notes = []
        if best_cand["route_status"] == "DIVERTED":
            caution_notes.append("Internal road grid partially severed by chemical plume; peripheral clearance route engaged.")
        if not best_cand["is_upwind"]:
            caution_notes.append(f"Move crosswind immediately to maintain >{best_cand['angular_clearance_deg']:.0f}° separation from vapor axis.")

        primary_result = EvacuationRouteResult(
            origin_name=origin_name,
            origin_coords=origin_coords,
            recommended_assembly_point_id=chosen_ap.id,
            recommended_assembly_point_name=chosen_ap.name,
            assembly_point_coords=[chosen_ap.lat, chosen_ap.lon],
            recommended_gate_id=chosen_gate.id,
            recommended_gate_name=chosen_gate.name,
            gate_coords=[chosen_gate.lat, chosen_gate.lon],
            total_distance_m=round(total_dist_m, 1),
            estimated_evac_time_min=est_time_min,
            route_status=best_cand["route_status"],
            route_coordinates=route_coords,
            route_geojson=route_geojson,
            steps=steps,
            avoided_blocked_roads=avoided_roads,
            caution_notes=caution_notes,
            score_breakdown=score_breakdown,
            candidate_routes=candidate_summaries,
            rejected_alternatives=rejected_summaries
        )

        # Secondary route (backup)
        secondary_cand = candidate_evaluations[1] if len(candidate_evaluations) > 1 else None

        return EvacuationPlanResponse(
            primary_evacuation_route=primary_result,
            secondary_evacuation_route=None,
            candidate_routes=candidate_summaries,
            rejected_alternatives=rejected_summaries,
            all_worker_evacuation_summary={
                "total_muster_assigned": impact_result.affected_workers_count,
                "primary_assembly_point": chosen_ap.name,
                "primary_gate": chosen_gate.name,
                "backup_assembly_point": secondary_cand["ap"].name if secondary_cand else "Assembly Point 4 - East Outer Staging Area",
                "evacuation_status": "ACTIVE_EVACUATION_EN_ROUTE",
                "plume_travel_direction": f"{plume_travel_deg:.0f}°"
            }
        )

evacuation_service = EvacuationService()

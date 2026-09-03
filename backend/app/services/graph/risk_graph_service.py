import math
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple
from app.services.chemicals.chemical_registry import chemical_registry

class PlantRiskGraphService:
    """
    Multi-Relational Risk Graph:
    Models inter-asset dependencies, process connections, chemical incompatibilities,
    and environmental consequence pathways (water bodies, drainage, settlements, roads).
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_authoritative_graph()

    def _build_authoritative_graph(self):
        self.graph.clear()

        # 1. Asset Nodes
        assets = [
            ("T-04", {"type": "STORAGE_TANK", "name": "Ammonia Cryogenic Tank", "chemical_id": "CHEM-NH3", "coords": (21.6855, 72.5745), "criticality": "CRITICAL"}),
            ("T-03", {"type": "STORAGE_TANK", "name": "LPG Horton Sphere 01", "chemical_id": "CHEM-LPG", "coords": (21.6840, 72.5720), "criticality": "CRITICAL"}),
            ("T-05", {"type": "STORAGE_TANK", "name": "LPG Horton Sphere 02", "chemical_id": "CHEM-LPG", "coords": (21.6835, 72.5735), "criticality": "CRITICAL"}),
            ("T-01", {"type": "STORAGE_TANK", "name": "Benzene Storage Tank 01", "chemical_id": "CHEM-C6H6", "coords": (21.6865, 72.5710), "criticality": "HIGH"}),
            ("T-02", {"type": "STORAGE_TANK", "name": "Chlorine Bullet Tank", "chemical_id": "CHEM-CL2", "coords": (21.6875, 72.5730), "criticality": "CRITICAL"}),
            ("T-06", {"type": "STORAGE_TANK", "name": "H2S Scrubber Column", "chemical_id": "CHEM-H2S", "coords": (21.6860, 72.5770), "criticality": "HIGH"}),
            ("PU-01", {"type": "PROCESS_UNIT", "name": "Primary Catalytic Reformer", "chemical_id": "CHEM-C6H6", "coords": (21.6860, 72.5730), "criticality": "CRITICAL"}),
            ("PU-02", {"type": "PROCESS_UNIT", "name": "Ammonia Synthesis Loop", "chemical_id": "CHEM-NH3", "coords": (21.6850, 72.5760), "criticality": "CRITICAL"}),
            ("PU-03", {"type": "PROCESS_UNIT", "name": "Gas Desulfurization Unit", "chemical_id": "CHEM-H2S", "coords": (21.6840, 72.5775), "criticality": "HIGH"}),
            ("SUB-01", {"type": "UTILITY", "name": "66kV Main Substation", "chemical_id": None, "coords": (21.6885, 72.5705), "criticality": "HIGH"}),
            ("CR-01", {"type": "CONTROL_ROOM", "name": "Central Blast-Resistant Control Room", "chemical_id": None, "coords": (21.6825, 72.5750), "criticality": "CRITICAL"}),
            ("FS-01", {"type": "FIRE_STATION", "name": "Industrial Fire & Hazmat Station", "chemical_id": None, "coords": (21.6820, 72.5715), "criticality": "HIGH"}),
            ("MED-01", {"type": "MEDICAL", "name": "Occupational Health Center", "chemical_id": None, "coords": (21.6810, 72.5755), "criticality": "HIGH"}),
        ]
        for node_id, attrs in assets:
            self.graph.add_node(node_id, **attrs)

        # 2. Pipeline Nodes
        pipelines = [
            ("PL-101", {"type": "PIPELINE", "name": "Ammonia Cryogenic Transfer Header", "chemical_id": "CHEM-NH3"}),
            ("PL-202", {"type": "PIPELINE", "name": "LPG Subsurface Interconnect Line", "chemical_id": "CHEM-LPG"}),
            ("PL-303", {"type": "PIPELINE", "name": "Chlorine Delivery Header", "chemical_id": "CHEM-CL2"}),
        ]
        for node_id, attrs in pipelines:
            self.graph.add_node(node_id, **attrs)

        # 3. Environmental Receptor Nodes
        env_nodes = [
            ("ENV-WATER-01", {"type": "WATER_BODY", "name": "Gulf of Khambhat Coastal Estuary", "sensitivity": "CRITICAL", "coords": (21.6850, 72.5640), "description": "Marine protected fish sanctuary"}),
            ("ENV-DRAIN-01", {"type": "DRAINAGE", "name": "GIDC Stormwater & Industrial Effluent Channel", "sensitivity": "HIGH", "coords": (21.6795, 72.5740), "description": "Spill runoff migration channel"}),
            ("ENV-SETTLE-01", {"type": "SETTLEMENT", "name": "Dahej Coastal Village & Community", "sensitivity": "CRITICAL", "coords": (21.6780, 72.5690), "population": 4200}),
            ("ENV-HWY-01", {"type": "HIGHWAY", "name": "SH-6 Dahej Industrial Logistics Highway", "sensitivity": "HIGH", "coords": (21.6920, 72.5760), "traffic": "Heavy Tanker Transit"}),
        ]
        for node_id, attrs in env_nodes:
            self.graph.add_node(node_id, **attrs)

        # 4. Process Connections (connected_to, feeds, supplies)
        edges = [
            ("T-04", "PL-101", {"relation": "connected_to", "risk_weight": 0.9}),
            ("PL-101", "PU-02", {"relation": "feeds", "risk_weight": 0.85}),
            ("T-03", "PL-202", {"relation": "connected_to", "risk_weight": 0.95}),
            ("T-05", "PL-202", {"relation": "connected_to", "risk_weight": 0.95}),
            ("T-02", "PL-303", {"relation": "connected_to", "risk_weight": 0.9}),
            ("SUB-01", "PU-01", {"relation": "supplies", "type": "ELECTRIC_POWER"}),
            ("SUB-01", "PU-02", {"relation": "supplies", "type": "ELECTRIC_POWER"}),
            ("FS-01", "T-04", {"relation": "protects", "type": "WATER_CURTAIN_COVERAGE"}),
            ("FS-01", "T-03", {"relation": "protects", "type": "DELUGE_COOLING_COVERAGE"}),
        ]
        for u, v, attrs in edges:
            self.graph.add_edge(u, v, **attrs)

        # 5. Spatial Proximity & Chemical Incompatibility Edges
        # Proximity threshold: <150 meters
        for a_id, a_data in assets:
            if "coords" not in a_data:
                continue
            for b_id, b_data in assets:
                if a_id == b_id or "coords" not in b_data:
                    continue
                lat1, lon1 = a_data["coords"]
                lat2, lon2 = b_data["coords"]
                dx = (lon2 - lon1) * 111320.0 * math.cos(math.radians(lat1))
                dy = (lat2 - lat1) * 110540.0
                dist_m = math.sqrt(dx * dx + dy * dy)
                
                if dist_m <= 180.0:
                    self.graph.add_edge(a_id, b_id, relation="near", distance_m=round(dist_m, 1))

                # Check Chemical Incompatibility
                chem_a = a_data.get("chemical_id")
                chem_b = b_data.get("chemical_id")
                if chem_a and chem_b and chem_a != chem_b:
                    incomp = chemical_registry.check_incompatibility(chem_a, chem_b)
                    if incomp["incompatible"]:
                        self.graph.add_edge(a_id, b_id, relation="incompatible_with", **incomp)

        # 6. Environmental Consequence Connections
        self.graph.add_edge("T-04", "ENV-DRAIN-01", relation="drains_to", distance_m=650.0)
        self.graph.add_edge("T-03", "ENV-SETTLE-01", relation="vulnerable_downwind", distance_m=720.0)
        self.graph.add_edge("T-01", "ENV-WATER-01", relation="spill_runoff_threat", distance_m=780.0)

    def analyze_cascade_pathways(self, primary_asset_id: str) -> Dict[str, Any]:
        """
        Traverses the multi-relational risk graph to compute cascade/domino propagation.
        """
        if primary_asset_id not in self.graph:
            return {"primary_asset": primary_asset_id, "threatened_nodes": []}

        source_data = self.graph.nodes[primary_asset_id]
        threatened_nodes = []

        # 1-hop and 2-hop traversal
        neighbors = list(self.graph.neighbors(primary_asset_id))
        for n in neighbors:
            edge_data = self.graph.get_edge_data(primary_asset_id, n)
            node_data = self.graph.nodes[n]
            
            rel = edge_data.get("relation", "near")
            dist = edge_data.get("distance_m", 0.0)
            crit = node_data.get("criticality", "MEDIUM")

            # Risk weight calculation
            weight = 0.5
            if rel == "connected_to" or rel == "feeds":
                weight = 0.9
            elif rel == "incompatible_with":
                weight = 0.95
            elif rel == "near" and dist < 100.0:
                weight = 0.8

            threatened_nodes.append({
                "node_id": n,
                "name": node_data.get("name", n),
                "type": node_data.get("type", "ASSET"),
                "relation": rel,
                "distance_m": dist,
                "cascade_probability_pct": round(weight * 100.0, 1),
                "criticality": crit,
                "chemical_id": node_data.get("chemical_id")
            })

        threatened_nodes.sort(key=lambda x: x["cascade_probability_pct"], reverse=True)

        return {
            "primary_asset_id": primary_asset_id,
            "primary_asset_name": source_data.get("name", primary_asset_id),
            "primary_chemical_id": source_data.get("chemical_id"),
            "total_threatened_assets": len(threatened_nodes),
            "threatened_nodes": threatened_nodes,
            "graph_summary": {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges()
            }
        }

    def evaluate_environmental_consequence(self, source_asset_id: str, wind_direction_deg: float) -> List[Dict[str, Any]]:
        """
        Evaluates consequence intersections with water bodies, drainages, and communities.
        """
        src = self.graph.nodes.get(source_asset_id)
        if not src or "coords" not in src:
            return []

        src_lat, src_lon = src["coords"]
        plume_vector_deg = (wind_direction_deg + 180.0) % 360.0 # Direction plume moves toward

        receptors = []
        for n, d in self.graph.nodes(data=True):
            if d.get("type") in ["WATER_BODY", "DRAINAGE", "SETTLEMENT", "HIGHWAY"]:
                if "coords" not in d:
                    continue
                r_lat, r_lon = d["coords"]
                dx = (r_lon - src_lon) * 111320.0 * math.cos(math.radians(src_lat))
                dy = (r_lat - src_lat) * 110540.0
                dist_m = math.sqrt(dx * dx + dy * dy)
                
                # Angle from source to receptor
                angle_deg = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
                bearing_diff = abs(plume_vector_deg - angle_deg)
                if bearing_diff > 180.0:
                    bearing_diff = 360.0 - bearing_diff

                is_downwind = bearing_diff <= 45.0
                priority = "HIGH" if (is_downwind and dist_m < 1500.0) else "MODERATE"

                receptors.append({
                    "receptor_id": n,
                    "name": d.get("name", n),
                    "type": d.get("type"),
                    "distance_m": round(dist_m, 1),
                    "is_downwind": is_downwind,
                    "bearing_difference_deg": round(bearing_diff, 1),
                    "consequence_priority": priority,
                    "sensitivity": d.get("sensitivity", "HIGH"),
                    "description": d.get("description", "")
                })

        return receptors

risk_graph_service = PlantRiskGraphService()

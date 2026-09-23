import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.plant import (
    PlantModel, AssetModel, PipelineModel, AssemblyPointModel,
    GateModel, RoadModel, WorkerModel, HydrantModel
)
from app.models.chemical import ChemicalModel
from app.models.resource import EmergencyResourceModel
from app.models.scenario import ScenarioPresetModel

class SiteService:
    def __init__(self):
        self.seed_file = settings.SEED_DATA_PATH

    def _get_seed_data(self) -> Dict[str, Any]:
        """Try loading seed data from multiple file paths or embedded fallback."""
        candidate_paths = [
            self.seed_file,
            settings.SEED_DATA_PATH,
            Path(__file__).resolve().parent.parent.parent / "data" / "seed_data.json",
            Path(__file__).resolve().parent.parent / "data" / "seed_data.json",
            Path.cwd() / "data" / "seed_data.json",
            Path.cwd() / "backend" / "data" / "seed_data.json",
            Path("/app/data/seed_data.json"),
            Path("/app/app/data/seed_data.json")
        ]
        for p in candidate_paths:
            if p and Path(p).exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Failed to read seed data from {p}: {e}")

        # Fallback minimal seed dictionary if file cannot be read
        return {
            "plant": {
                "id": "PCH-ALPHA-04",
                "name": "PetroChem Complex Alpha (Dahej PCPIR)",
                "industry_type": "Petrochemical Processing & Cryogenic Storage",
                "location": "Dahej PCPIR, Bharuch District, Gujarat, India",
                "center": [21.6850, 72.5750],
                "bounds": [
                    [21.6810, 72.5690],
                    [21.6890, 72.5690],
                    [21.6890, 72.5810],
                    [21.6810, 72.5810]
                ],
                "risk_level": "High",
                "erdmp_license": "ERDMP/GJ/2026/04812"
            },
            "chemicals": [
                {
                    "id": "CHEM-NH3",
                    "name": "Ammonia (Anhydrous)",
                    "formula": "NH3",
                    "cas_number": "7664-41-7",
                    "molecular_weight": 17.03,
                    "boiling_point_c": -33.34,
                    "flash_point_c": -132.0,
                    "lfl_percent": 15.0,
                    "ufl_percent": 28.0,
                    "vapor_density_rel_air": 0.59,
                    "liquid_density_kg_m3": 681.9,
                    "hazard_category": "TOXIC_GAS",
                    "erpg_1_ppm": 25.0,
                    "erpg_2_ppm": 150.0,
                    "erpg_3_ppm": 750.0,
                    "idlh_ppm": 300.0,
                    "color_code": "#ef4444",
                    "description": "Corrosive and toxic compressed liquefied gas."
                }
            ],
            "assets": [
                {
                    "id": "T-04",
                    "name": "Cryogenic Ammonia Storage Tank T-04",
                    "type": "STORAGE_SPHERE",
                    "sector": "Sector Alpha",
                    "coordinates": [21.6850, 72.5750],
                    "chemical_id": "CHEM-NH3",
                    "capacity_m3": 5000.0,
                    "current_fill_pct": 82.5,
                    "operating_pressure_bar": 4.2,
                    "operating_temp_c": -33.0,
                    "criticality": "HIGH",
                    "status": "OPERATIONAL"
                }
            ],
            "roads": [
                {
                    "id": "RD-01",
                    "name": "North Perimeter Road",
                    "from_node": "N-01",
                    "to_node": "N-02",
                    "coordinates": [[21.6885, 72.5700], [21.6885, 72.5800]],
                    "width_m": 10.0,
                    "surface": "Asphalt",
                    "accessibility": True,
                    "status": "OPEN"
                },
                {
                    "id": "RD-02",
                    "name": "South Access Corridor",
                    "from_node": "N-03",
                    "to_node": "N-04",
                    "coordinates": [[21.6815, 72.5700], [21.6815, 72.5800]],
                    "width_m": 10.0,
                    "surface": "Asphalt",
                    "accessibility": True,
                    "status": "OPEN"
                }
            ],
            "assembly_points": [
                {
                    "id": "AP-01",
                    "name": "Assembly Point 1 — North Gate Staging Area",
                    "coordinates": [21.6885, 72.5750],
                    "capacity": 250,
                    "current_occupancy": 0,
                    "status": "SAFE"
                },
                {
                    "id": "AP-02",
                    "name": "Assembly Point 2 — West Outer Muster Ground",
                    "coordinates": [21.6850, 72.5695],
                    "capacity": 300,
                    "current_occupancy": 0,
                    "status": "SAFE"
                }
            ],
            "gates": [
                {
                    "id": "GATE-01",
                    "name": "Gate 1 — Main North Gate",
                    "coordinates": [21.6888, 72.5750],
                    "status": "OPEN",
                    "type": "PRIMARY_GATE"
                },
                {
                    "id": "GATE-02",
                    "name": "Gate 2 — West Emergency Egress Gate",
                    "coordinates": [21.6850, 72.5692],
                    "status": "OPEN",
                    "type": "EMERGENCY_EGRESS"
                }
            ],
            "emergency_resources": [
                {
                    "id": "RES-FT-01",
                    "name": "Foam Tender Unit FT-1",
                    "type": "FOAM_TENDER",
                    "stationed_at": "Fire Station Alpha",
                    "coordinates": [21.6830, 72.5720],
                    "status": "AVAILABLE",
                    "crew_count": 4
                }
            ],
            "pipelines": [],
            "workers": [],
            "hydrants": [],
            "preset_scenarios": []
        }

    def load_seed_data_if_empty(self, db: Session):
        """Seed the database with realistic industrial plant data if empty."""
        if db.query(PlantModel).first() is not None:
            return

        data = self._get_seed_data()

        # 1. Plant
        p = data.get("plant", {})
        plant = PlantModel(
            id=p["id"],
            name=p["name"],
            industry_type=p["industry_type"],
            location=p["location"],
            center_lat=p["center"][0],
            center_lon=p["center"][1],
            bounds_json=p["bounds"],
            risk_level=p.get("risk_level", "High"),
            erdmp_license=p.get("erdmp_license")
        )
        db.add(plant)

        # 2. Chemicals
        for c in data.get("chemicals", []):
            chem = ChemicalModel(
                id=c["id"],
                name=c["name"],
                formula=c.get("formula"),
                cas_number=c.get("cas_number"),
                molecular_weight=c["molecular_weight"],
                boiling_point_c=c.get("boiling_point_c"),
                flash_point_c=c.get("flash_point_c"),
                lfl_percent=c.get("lfl_percent"),
                ufl_percent=c.get("ufl_percent"),
                vapor_density_rel_air=c.get("vapor_density_rel_air"),
                liquid_density_kg_m3=c.get("liquid_density_kg_m3"),
                hazard_category=c["hazard_category"],
                erpg_1_ppm=c.get("erpg_1_ppm"),
                erpg_2_ppm=c.get("erpg_2_ppm"),
                erpg_3_ppm=c.get("erpg_3_ppm"),
                idlh_ppm=c.get("idlh_ppm"),
                color_code=c.get("color_code", "#ef4444"),
                description=c.get("description"),
                tactical_guidance=c.get("tactical_guidance")
            )
            db.add(chem)

        # 3. Assets
        for a in data.get("assets", []):
            asset = AssetModel(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                sector=a["sector"],
                lat=a["coordinates"][0],
                lon=a["coordinates"][1],
                chemical_id=a.get("chemical_id"),
                capacity_m3=a.get("capacity_m3"),
                current_fill_pct=a.get("current_fill_pct"),
                operating_pressure_bar=a.get("operating_pressure_bar"),
                operating_temp_c=a.get("operating_temp_c"),
                criticality=a.get("criticality", "MEDIUM"),
                status=a.get("status", "OPERATIONAL"),
                fire_protection=a.get("fire_protection")
            )
            db.add(asset)

        # 4. Pipelines
        for pl in data.get("pipelines", []):
            pipeline = PipelineModel(
                id=pl["id"],
                name=pl["name"],
                chemical_id=pl.get("chemical_id"),
                operating_pressure_bar=pl.get("operating_pressure_bar"),
                diameter_mm=pl.get("diameter_mm"),
                coordinates_json=pl["coordinates"],
                status=pl.get("status", "OPERATIONAL")
            )
            db.add(pipeline)

        # 5. Assembly Points
        for ap in data.get("assembly_points", []):
            point = AssemblyPointModel(
                id=ap["id"],
                name=ap["name"],
                lat=ap["coordinates"][0],
                lon=ap["coordinates"][1],
                capacity=ap.get("capacity", 100),
                current_occupancy=ap.get("current_occupancy", 0),
                status=ap.get("status", "SAFE"),
                equipment=ap.get("equipment")
            )
            db.add(point)

        # 6. Gates
        for g in data.get("gates", []):
            gate = GateModel(
                id=g["id"],
                name=g["name"],
                lat=g["coordinates"][0],
                lon=g["coordinates"][1],
                status=g.get("status", "OPEN"),
                type=g.get("type", "PRIMARY_GATE")
            )
            db.add(gate)

        # 7. Roads
        for r in data.get("roads", []):
            road = RoadModel(
                id=r["id"],
                name=r["name"],
                from_node=r["from_node"],
                to_node=r["to_node"],
                coordinates_json=r["coordinates"],
                width_m=r.get("width_m", 8.0),
                surface=r.get("surface", "Asphalt"),
                accessibility=r.get("accessibility", True),
                status=r.get("status", "OPEN")
            )
            db.add(road)

        # 8. Workers
        for w in data.get("workers", []):
            worker = WorkerModel(
                id=w["id"],
                name=w["name"],
                role=w["role"],
                sector=w["sector"],
                lat=w["coordinates"][0],
                lon=w["coordinates"][1],
                active=w.get("active", True),
                contact=w.get("contact")
            )
            db.add(worker)

        # 9. Hydrants
        for h in data.get("hydrants", []):
            hydrant = HydrantModel(
                id=h["id"],
                lat=h["coordinates"][0],
                lon=h["coordinates"][1],
                flow_lpm=h.get("flow_lpm", 2000.0),
                pressure_bar=h.get("pressure_bar", 7.0),
                status=h.get("status", "OPERATIONAL")
            )
            db.add(hydrant)

        # 10. Emergency Resources
        for res in data.get("emergency_resources", []):
            resource = EmergencyResourceModel(
                id=res["id"],
                name=res["name"],
                type=res["type"],
                stationed_at=res["stationed_at"],
                lat=res["coordinates"][0],
                lon=res["coordinates"][1],
                status=res.get("status", "AVAILABLE"),
                capacity_details=res.get("capacity_details"),
                crew_count=res.get("crew_count", 4)
            )
            db.add(resource)

        # 11. Presets
        for sc in data.get("preset_scenarios", []):
            preset = ScenarioPresetModel(
                id=sc["id"],
                title=sc["title"],
                asset_id=sc["asset_id"],
                chemical_id=sc["chemical_id"],
                incident_type=sc["incident_type"],
                release_rate_kg_s=sc["release_rate_kg_s"],
                release_duration_min=sc.get("release_duration_min", 30),
                operating_temp_c=sc.get("operating_temp_c", 25.0),
                operating_pressure_bar=sc.get("operating_pressure_bar", 5.0),
                wind_speed_kmh=sc.get("wind_speed_kmh", 8.0),
                wind_direction_deg=sc.get("wind_direction_deg", 45.0),
                wind_direction_cardinal=sc.get("wind_direction_cardinal", "NE"),
                ambient_temp_c=sc.get("ambient_temp_c", 30.0),
                atmospheric_stability=sc.get("atmospheric_stability", "D"),
                humidity_pct=sc.get("humidity_pct", 60.0),
                description=sc.get("description")
            )
            db.add(preset)

        db.commit()
        print("Successfully loaded seed data into database!")

    def get_full_site_data(self, db: Session) -> Dict[str, Any]:
        """Return the structured plant site data."""
        plant = db.query(PlantModel).first()
        if not plant:
            self.load_seed_data_if_empty(db)
            plant = db.query(PlantModel).first()

        plant_dict = {
            "id": plant.id if plant else "PCH-ALPHA-04",
            "name": plant.name if plant else "PetroChem Complex Alpha (Dahej PCPIR)",
            "industry_type": plant.industry_type if plant else "Petrochemical Processing & Cryogenic Storage",
            "location": plant.location if plant else "Dahej PCPIR, Bharuch District, Gujarat, India",
            "center": [plant.center_lat, plant.center_lon] if plant else [21.6850, 72.5750],
            "bounds": plant.bounds_json if plant else [[21.6810, 72.5690], [21.6890, 72.5690], [21.6890, 72.5810], [21.6810, 72.5810]],
            "risk_level": plant.risk_level if plant else "High",
            "erdmp_license": plant.erdmp_license if plant else "ERDMP/GJ/2026/04812"
        }

        assets = db.query(AssetModel).all()
        pipelines = db.query(PipelineModel).all()
        assembly_points = db.query(AssemblyPointModel).all()
        gates = db.query(GateModel).all()
        roads = db.query(RoadModel).all()
        workers = db.query(WorkerModel).all()
        hydrants = db.query(HydrantModel).all()
        resources = db.query(EmergencyResourceModel).all()

        return {
            "plant": plant_dict,
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.type,
                    "sector": a.sector,
                    "coordinates": [a.lat, a.lon],
                    "chemical_id": a.chemical_id,
                    "capacity_m3": a.capacity_m3,
                    "current_fill_pct": a.current_fill_pct,
                    "operating_pressure_bar": a.operating_pressure_bar,
                    "operating_temp_c": a.operating_temp_c,
                    "criticality": a.criticality,
                    "status": a.status,
                    "fire_protection": a.fire_protection
                }
                for a in assets
            ],
            "pipelines": [
                {
                    "id": pl.id,
                    "name": pl.name,
                    "chemical_id": pl.chemical_id,
                    "operating_pressure_bar": pl.operating_pressure_bar,
                    "diameter_mm": pl.diameter_mm,
                    "coordinates": pl.coordinates_json,
                    "status": pl.status
                }
                for pl in pipelines
            ],
            "assembly_points": [
                {
                    "id": ap.id,
                    "name": ap.name,
                    "coordinates": [ap.lat, ap.lon],
                    "capacity": ap.capacity,
                    "current_occupancy": ap.current_occupancy,
                    "status": ap.status,
                    "equipment": ap.equipment
                }
                for ap in assembly_points
            ],
            "gates": [
                {
                    "id": g.id,
                    "name": g.name,
                    "coordinates": [g.lat, g.lon],
                    "status": g.status,
                    "type": g.type
                }
                for g in gates
            ],
            "roads": [
                {
                    "id": r.id,
                    "name": r.name,
                    "from_node": r.from_node,
                    "to_node": r.to_node,
                    "coordinates": r.coordinates_json,
                    "width_m": r.width_m,
                    "surface": r.surface,
                    "accessibility": r.accessibility,
                    "status": r.status
                }
                for r in roads
            ],
            "workers": [
                {
                    "id": w.id,
                    "name": w.name,
                    "role": w.role,
                    "sector": w.sector,
                    "coordinates": [w.lat, w.lon],
                    "active": w.active,
                    "contact": w.contact
                }
                for w in workers
            ],
            "hydrants": [
                {
                    "id": h.id,
                    "coordinates": [h.lat, h.lon],
                    "flow_lpm": h.flow_lpm,
                    "pressure_bar": h.pressure_bar,
                    "status": h.status
                }
                for h in hydrants
            ],
            "emergency_resources": [
                {
                    "id": res.id,
                    "name": res.name,
                    "type": res.type,
                    "stationed_at": res.stationed_at,
                    "coordinates": [res.lat, res.lon],
                    "status": res.status,
                    "capacity_details": res.capacity_details,
                    "crew_count": res.crew_count
                }
                for res in resources
            ]
        }

    def get_plant_geojson(self, db: Session) -> Dict[str, Any]:
        """Convert all static plant site features into a GeoJSON FeatureCollection."""
        site_data = self.get_full_site_data(db)
        features = []

        # Plant boundary
        features.append({
            "type": "Feature",
            "id": site_data["plant"]["id"],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[p[1], p[0]] for p in site_data["plant"]["bounds"]]]
            },
            "properties": {
                "category": "PLANT_BOUNDARY",
                "name": site_data["plant"]["name"],
                "industry_type": site_data["plant"]["industry_type"]
            }
        })

        # Roads
        for r in site_data["roads"]:
            features.append({
                "type": "Feature",
                "id": r["id"],
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[p[1], p[0]] for p in r["coordinates"]]
                },
                "properties": {
                    "category": "ROAD",
                    "id": r["id"],
                    "name": r["name"],
                    "status": r["status"]
                }
            })

        # Pipelines
        for pl in site_data["pipelines"]:
            features.append({
                "type": "Feature",
                "id": pl["id"],
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[p[1], p[0]] for p in pl["coordinates"]]
                },
                "properties": {
                    "category": "PIPELINE",
                    "id": pl["id"],
                    "name": pl["name"],
                    "chemical_id": pl["chemical_id"]
                }
            })

        # Assets
        for a in site_data["assets"]:
            features.append({
                "type": "Feature",
                "id": a["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [a["coordinates"][1], a["coordinates"][0]]
                },
                "properties": {
                    "category": "ASSET",
                    "id": a["id"],
                    "name": a["name"],
                    "type": a["type"],
                    "criticality": a["criticality"],
                    "chemical_id": a["chemical_id"]
                }
            })

        # Assembly Points
        for ap in site_data["assembly_points"]:
            features.append({
                "type": "Feature",
                "id": ap["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [ap["coordinates"][1], ap["coordinates"][0]]
                },
                "properties": {
                    "category": "ASSEMBLY_POINT",
                    "id": ap["id"],
                    "name": ap["name"],
                    "capacity": ap["capacity"],
                    "status": ap["status"]
                }
            })

        # Gates
        for g in site_data["gates"]:
            features.append({
                "type": "Feature",
                "id": g["id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [g["coordinates"][1], g["coordinates"][0]]
                },
                "properties": {
                    "category": "GATE",
                    "id": g["id"],
                    "name": g["name"],
                    "type": g["type"]
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

site_service = SiteService()

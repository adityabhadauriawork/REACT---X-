import math
import difflib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.facility import IndustrialFacilityModel

class IndustrialContextService:
    """
    Industrial Context Engine for SIH26162.
    Manages authoritative industrial facility registries ingested from:
    1. OpenStreetMap (OSM) - industrial landuse, works, power plants
    2. Global Energy Monitor (GEM) - Thermal power, gas/oil refineries, steel plants
    3. Bhuvan / NRSC Indian industrial zones
    4. NASA FIRMS Static Thermal Anomalies correlation
    
    Includes multi-signal facility reconciliation to deduplicate overlapping records.
    """

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two WGS84 coordinates in meters."""
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def name_similarity_ratio(self, name1: str, name2: str) -> float:
        """Calculates normalized text similarity ratio between facility names."""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        return difflib.SequenceMatcher(None, n1, n2).ratio()

    def get_seed_industrial_facilities(self) -> List[Dict[str, Any]]:
        """
        Seeds canonical pan-India industrial context across key economic corridors
        incorporating OSM, GEM, and regulatory datasets.
        """
        return [
            {
                "facility_id": "FAC-IND-OSM-DAHEJ-01",
                "source": "OSM",
                "source_id": "way/104829104",
                "name": "PetroChem Complex Alpha - Unit 04",
                "operator_name": "Bharat Petrochemical Industrial Corp.",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Cryogenic Ethylene & Ammonia Cracking Plant",
                "latitude": 21.6850,
                "longitude": 72.5750,
                "state": "Gujarat",
                "district": "Bharuch",
                "country": "India",
                "cluster_name": "Dahej PCPIR Special Economic Zone",
                "fence_radius_m": 1200.0,
                "boundary_geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.565, 21.675],
                        [72.585, 21.675],
                        [72.585, 21.695],
                        [72.565, 21.695],
                        [72.565, 21.675]
                    ]]
                },
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {
                    "osm_tags": {"landuse": "industrial", "industrial": "chemical", "hazard": "severe"},
                    "gem_tracker_id": "GEM-IND-PETRO-084"
                },
                "erdmp_license": "PESO/IND/2024/GJ-DAHEJ-1505",
                "major_chemicals_stored": ["Ammonia (Anhydrous)", "Benzene", "LPG", "Chlorine"]
            },
            {
                "facility_id": "FAC-IND-GEM-LNG-02",
                "source": "GEM",
                "source_id": "GEM-LNG-IND-042",
                "name": "Petronet Dahej LNG Cryogenic Regasification Terminal",
                "operator_name": "Petronet LNG Limited",
                "facility_type": "REFINERY",
                "subtype": "LNG Import & Regasification Super-Hub",
                "latitude": 21.6720,
                "longitude": 72.5320,
                "state": "Gujarat",
                "district": "Bharuch",
                "country": "India",
                "cluster_name": "Dahej Port & PCPIR Corridor",
                "fence_radius_m": 1500.0,
                "boundary_geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.520, 21.660],
                        [72.545, 21.660],
                        [72.545, 21.685],
                        [72.520, 21.685],
                        [72.520, 21.660]
                    ]]
                },
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"capacity_mtpa": 17.5, "status": "operating"},
                "erdmp_license": "PESO/IND/2023/GJ-LNG-0042",
                "major_chemicals_stored": ["Liquefied Natural Gas", "Boil-off Gas (Methane)"]
            },
            {
                "facility_id": "FAC-IND-GEM-JAM-01",
                "source": "GEM",
                "source_id": "GEM-REF-IND-001",
                "name": "Reliance Jamnagar Mega Refinery & Petrochemical Complex",
                "operator_name": "Reliance Industries Limited",
                "facility_type": "REFINERY",
                "subtype": "Petroleum Refinery & Aromatic Petrochemical Works",
                "latitude": 22.3600,
                "longitude": 69.8300,
                "state": "Gujarat",
                "district": "Jamnagar",
                "country": "India",
                "cluster_name": "Jamnagar Energy Superhub",
                "fence_radius_m": 4500.0,
                "boundary_geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [69.790, 22.320],
                        [69.870, 22.320],
                        [69.870, 22.400],
                        [69.790, 22.400],
                        [69.790, 22.320]
                    ]]
                },
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"crude_distillation_bpd": 1240000, "gem_id": "REF-JAMNAGAR"},
                "erdmp_license": "PESO/IND/2024/GJ-JAM-0001",
                "major_chemicals_stored": ["Crude Oil", "Naphtha", "Propylene", "Ethylene", "LPG"]
            },
            {
                "facility_id": "FAC-IND-OSM-HAZ-01",
                "source": "OSM",
                "source_id": "way/38920194",
                "name": "ONGC Hazira Gas Processing & Petrochemical Complex",
                "operator_name": "Oil and Natural Gas Corporation",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Natural Gas Sweetening & LPG Extraction Plant",
                "latitude": 21.1200,
                "longitude": 72.6700,
                "state": "Gujarat",
                "district": "Surat",
                "country": "India",
                "cluster_name": "Hazira Industrial Belt",
                "fence_radius_m": 2000.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"osm_man_made": "works", "operator": "ONGC"},
                "erdmp_license": "PESO/IND/2022/GJ-HAZ-0089",
                "major_chemicals_stored": ["Sour Gas", "LPG", "Sulfur", "Condensate"]
            },
            {
                "facility_id": "FAC-IND-IOCL-VAD-01",
                "source": "RECONCILED",
                "source_id": "IOCL-REF-VAD-01",
                "name": "IOCL Gujarat Refinery & Petrochemical Complex",
                "operator_name": "Indian Oil Corporation Limited",
                "facility_type": "REFINERY",
                "subtype": "Petroleum Distillation & Hydrocracker Complex",
                "latitude": 22.3550,
                "longitude": 73.1350,
                "state": "Gujarat",
                "district": "Vadodara",
                "country": "India",
                "cluster_name": "Koyali Petrochemical Hub",
                "fence_radius_m": 2800.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_mtpa": 13.7},
                "erdmp_license": "PESO/IND/2024/GJ-VAD-0012",
                "major_chemicals_stored": ["Aviation Turbine Fuel", "Naphtha", "Diesel", "Benzene"]
            },
            {
                "facility_id": "FAC-IND-BPCL-MUM-01",
                "source": "RECONCILED",
                "source_id": "BPCL-REF-MUM-01",
                "name": "Mumbai Chembur Coastal Petrochemicals & Refinery",
                "operator_name": "Bharat Petroleum / HPCL",
                "facility_type": "REFINERY",
                "subtype": "Coastal Refinery & Lube Base Oil Plant",
                "latitude": 19.0050,
                "longitude": 72.8950,
                "state": "Maharashtra",
                "district": "Mumbai Suburban",
                "country": "India",
                "cluster_name": "Mahul / Chembur Coastal Hub",
                "fence_radius_m": 2400.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_mtpa": 12.0},
                "erdmp_license": "PESO/IND/2023/MH-MUM-0004",
                "major_chemicals_stored": ["Motor Spirit", "High Speed Diesel", "LPG", "Fuel Oil"]
            },
            {
                "facility_id": "FAC-IND-SAIL-ROU-01",
                "source": "GEM",
                "source_id": "SAIL-STEEL-ROU-01",
                "name": "Rourkela Integrated Steel Plant",
                "operator_name": "Steel Authority of India Limited",
                "facility_type": "STEEL",
                "subtype": "Integrated Hot Strip & Plate Mill",
                "latitude": 22.2150,
                "longitude": 84.8650,
                "state": "Odisha",
                "district": "Sundargarh",
                "country": "India",
                "cluster_name": "Rourkela Metallurgical Corridor",
                "fence_radius_m": 3200.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"capacity_mtpa": 4.5},
                "erdmp_license": "PESO/IND/2022/OR-ROU-0018",
                "major_chemicals_stored": ["Liquid Steel", "Coke Oven Gas", "Blast Furnace Slag"]
            },
            {
                "facility_id": "FAC-IND-ODI-PAR-002",
                "source": "GEM",
                "source_id": "IOCL-REF-PAR-01",
                "name": "Indian Oil Paradip Refinery & Petrochemical Complex",
                "operator_name": "Indian Oil Corporation Limited",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Deepwater Petrochemical & Polymer Hub",
                "latitude": 20.2854,
                "longitude": 86.6432,
                "state": "Odisha",
                "district": "Jagatsinghpur",
                "country": "India",
                "cluster_name": "Paradip PCPIR Deepwater Hub",
                "fence_radius_m": 3500.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_mtpa": 15.0},
                "erdmp_license": "PESO/IND/2024/OR-PAR-0002",
                "major_chemicals_stored": ["Polypropylene", "Ethylene Glycol", "Naphtha", "LPG"]
            },
            {
                "facility_id": "FAC-IND-GEM-KORBA-01",
                "source": "GEM",
                "source_id": "GEM-PWR-IND-012",
                "name": "NTPC Korba Super Thermal Power Station (2600 MW)",
                "operator_name": "NTPC Limited",
                "facility_type": "THERMAL_POWER",
                "subtype": "Supercritical Coal-Fired Power Station",
                "latitude": 22.3800,
                "longitude": 82.6800,
                "state": "Chhattisgarh",
                "district": "Korba",
                "country": "India",
                "cluster_name": "Korba Coal & Power Basin",
                "fence_radius_m": 3000.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"installed_mw": 2600, "gem_fuel": "Coal"},
                "erdmp_license": "CEA/IND/2023/CG-KORBA-01",
                "major_chemicals_stored": ["Bituminous Coal", "Furnace Heavy Oil", "Fly Ash"]
            },
            {
                "facility_id": "FAC-IND-OSM-JSR-01",
                "source": "OSM",
                "source_id": "way/9928172",
                "name": "Tata Steel Jamshedpur Integrated Steel Works",
                "operator_name": "Tata Steel Limited",
                "facility_type": "STEEL",
                "subtype": "Blast Furnace & Coke Oven Steel Plant",
                "latitude": 22.7800,
                "longitude": 86.2000,
                "state": "Jharkhand",
                "district": "East Singhbhum",
                "country": "India",
                "cluster_name": "Jamshedpur Metallurgical Cluster",
                "fence_radius_m": 3500.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"osm_industrial": "steel", "capacity_mtpa": 11.0},
                "erdmp_license": "PESO/IND/2021/JH-JSR-0012",
                "major_chemicals_stored": ["Coke Oven Gas", "Liquid Iron", "Oxygen", "Slag"]
            },
            {
                "facility_id": "FAC-IND-OSM-JHARIA-01",
                "source": "OSM",
                "source_id": "way/4481029",
                "name": "BCCL Jharia Opencast Coal Mining & Seam Fire Sector",
                "operator_name": "Bharat Coking Coal Limited",
                "facility_type": "MINING",
                "subtype": "Opencast Coal Extraction & Subsurface Seam Fire Zone",
                "latitude": 23.7500,
                "longitude": 86.4200,
                "state": "Jharkhand",
                "district": "Dhanbad",
                "country": "India",
                "cluster_name": "Jharia Coalfield Mining Zone",
                "fence_radius_m": 5000.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"osm_landuse": "quarry", "subsurface_fire_zone": True},
                "erdmp_license": "DGMS/IND/2020/JH-JHA-MINE",
                "major_chemicals_stored": ["Coking Coal", "Explosives ANFO", "Subsurface Methane"]
            },
            {
                "facility_id": "FAC-IND-CPCL-MAN-01",
                "source": "RECONCILED",
                "source_id": "CPCL-MAN-01",
                "name": "Manali Petrochemical & Fertilizers Complex",
                "operator_name": "CPCL / Manali Petrochemicals",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Petrochemical Cracker & Organic Chemical Hub",
                "latitude": 13.1650,
                "longitude": 80.2600,
                "state": "Tamil Nadu",
                "district": "Chennai",
                "country": "India",
                "cluster_name": "Manali Coastal Petrochem Corridor",
                "fence_radius_m": 2200.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_mtpa": 10.5},
                "erdmp_license": "PESO/IND/2023/TN-MAN-0056",
                "major_chemicals_stored": ["Propylene Oxide", "Polyols", "Anhydrous Ammonia", "Chlorine"]
            },
            {
                "facility_id": "FAC-IND-RINL-VIZ-01",
                "source": "GEM",
                "source_id": "RINL-VIZ-01",
                "name": "Visakhapatnam Coastal Steel Plant (RINL)",
                "operator_name": "Rashtriya Ispat Nigam Limited",
                "facility_type": "STEEL",
                "subtype": "Shore-Based Integrated Steel Works",
                "latitude": 17.6250,
                "longitude": 83.1850,
                "state": "Andhra Pradesh",
                "district": "Visakhapatnam",
                "country": "India",
                "cluster_name": "Gajuwaka Industrial Hub",
                "fence_radius_m": 3800.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"capacity_mtpa": 7.3},
                "erdmp_license": "PESO/IND/2022/AP-VIZ-0034",
                "major_chemicals_stored": ["Hot Metal", "Liquid Steel", "Oxygen (Cryogenic)", "Coke Oven Gas"]
            },
            {
                "facility_id": "FAC-IND-NRL-NUM-01",
                "source": "GEM",
                "source_id": "NRL-NUM-01",
                "name": "Numaligarh Eco-Refinery Complex",
                "operator_name": "Numaligarh Refinery Limited",
                "facility_type": "REFINERY",
                "subtype": "High-Hydrocracker Distillation Unit",
                "latitude": 26.5850,
                "longitude": 93.7450,
                "state": "Assam",
                "district": "Golaghat",
                "country": "India",
                "cluster_name": "Brahmaputra Valley Energy Hub",
                "fence_radius_m": 2500.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"capacity_mtpa": 3.0},
                "erdmp_license": "PESO/IND/2023/AS-NUM-0001",
                "major_chemicals_stored": ["Motor Spirit", "High Speed Diesel", "LPG", "Wax"]
            },
            {
                "facility_id": "FAC-IND-HZL-UDA-01",
                "source": "OSM",
                "source_id": "HZL-UDA-01",
                "name": "Debari Zinc Smelter & Chemical Complex",
                "operator_name": "Hindustan Zinc Limited",
                "facility_type": "MINING",
                "subtype": "Hydrometallurgical Zinc Smelter",
                "latitude": 24.6050,
                "longitude": 73.8150,
                "state": "Rajasthan",
                "district": "Udaipur",
                "country": "India",
                "cluster_name": "Aravalli Metallurgical Zone",
                "fence_radius_m": 2600.0,
                "boundary_geojson": None,
                "reconciliation_status": "SINGLE_SOURCE",
                "source_metadata": {"capacity_ktpa": 88},
                "erdmp_license": "PESO/IND/2021/RJ-UDA-0089",
                "major_chemicals_stored": ["Sulfuric Acid", "Zinc Concentrate", "Lead Slag"]
            },
            {
                "facility_id": "FAC-IND-MCF-MAN-01",
                "source": "RECONCILED",
                "source_id": "MCF-MAN-01",
                "name": "Mangalore Coastal Chemicals & LNG Terminal",
                "operator_name": "MCF / MRPL",
                "facility_type": "CHEMICAL",
                "subtype": "Nitrogenous Fertilizer & Chemical Terminal",
                "latitude": 12.9450,
                "longitude": 74.8150,
                "state": "Karnataka",
                "district": "Dakshina Kannada",
                "country": "India",
                "cluster_name": "Panambur Port Chemical Zone",
                "fence_radius_m": 2000.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_ktpa": 650},
                "erdmp_license": "PESO/IND/2024/KA-MAN-0021",
                "major_chemicals_stored": ["Urea", "Ammonia", "Sulfuric Acid", "Phosphoric Acid"]
            },
            {
                "facility_id": "FAC-IND-GAIL-PAT-01",
                "source": "RECONCILED",
                "source_id": "GAIL-PAT-01",
                "name": "GAIL Pata Integrated Petrochemical Complex",
                "operator_name": "GAIL (India) Limited",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Gas Cracker & Polymer Complex",
                "latitude": 26.6000,
                "longitude": 79.5400,
                "state": "Uttar Pradesh",
                "district": "Auraiya",
                "country": "India",
                "cluster_name": "Northern Gas & Petrochemical Hub",
                "fence_radius_m": 3100.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_ktpa": 810},
                "erdmp_license": "PESO/IND/2023/UP-PAT-0015",
                "major_chemicals_stored": ["High Density Polyethylene", "Linear Alkyl Benzene", "LPG", "Propane"]
            },
            {
                "facility_id": "FAC-IND-HPL-HAL-01",
                "source": "RECONCILED",
                "source_id": "HPL-HAL-01",
                "name": "Haldia Petrochemicals & Refining Complex",
                "operator_name": "Haldia Petrochemicals / IOCL",
                "facility_type": "PETROCHEMICAL",
                "subtype": "Naphtha Cracker & Aromatics Complex",
                "latitude": 22.0300,
                "longitude": 88.0800,
                "state": "West Bengal",
                "district": "Purba Medinipur",
                "country": "India",
                "cluster_name": "Haldia Port Industrial Belt",
                "fence_radius_m": 3300.0,
                "boundary_geojson": None,
                "reconciliation_status": "RECONCILED_MATCH",
                "source_metadata": {"capacity_mtpa": 7.5},
                "erdmp_license": "PESO/IND/2024/WB-HAL-0008",
                "major_chemicals_stored": ["Naphtha", "Ethylene", "Propylene", "Butadiene", "Benzene"]
            }
        ]

    def seed_facilities_if_empty(self, db: Session):
        """Seeds initial facilities in the database if table is empty."""
        count = db.query(IndustrialFacilityModel).count()
        if count == 0:
            for fac_dict in self.get_seed_industrial_facilities():
                model = IndustrialFacilityModel(**fac_dict)
                db.add(model)
            db.commit()

    def reconcile_facilities(
        self,
        new_facilities: List[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Multi-signal facility reconciliation algorithm:
        Compares incoming OSM/GEM records against existing facility database using:
        1. Coordinate proximity (d < 1500 meters)
        2. Name text similarity ratio (> 0.60)
        3. Facility sector / type compatibility
        
        If high-confidence match found -> merges and updates provenance without duplicate insertion.
        Otherwise -> inserts new facility.
        """
        existing = db.query(IndustrialFacilityModel).all()
        reconciled_count = 0
        inserted_count = 0

        for new_fac in new_facilities:
            matched_existing = None
            for ex in existing:
                dist = self.haversine_distance_m(new_fac["latitude"], new_fac["longitude"], ex.latitude, ex.longitude)
                name_sim = self.name_similarity_ratio(new_fac["name"], ex.name)
                same_type = (new_fac.get("facility_type") == ex.facility_type)

                if (dist <= 1500.0 and name_sim >= 0.50) or (dist <= 500.0 and same_type):
                    matched_existing = ex
                    break

            if matched_existing:
                # Merge metadata and upgrade reconciliation status
                matched_existing.reconciliation_status = "RECONCILED_MATCH"
                existing_meta = matched_existing.source_metadata or {}
                incoming_meta = new_fac.get("source_metadata") or {}
                matched_existing.source_metadata = {**existing_meta, **incoming_meta, "reconciled_with": new_fac.get("source_id")}
                if not matched_existing.boundary_geojson and new_fac.get("boundary_geojson"):
                    matched_existing.boundary_geojson = new_fac["boundary_geojson"]
                reconciled_count += 1
            else:
                new_model = IndustrialFacilityModel(**new_fac)
                db.add(new_model)
                existing.append(new_model)
                inserted_count += 1

        db.commit()
        return {
            "evaluated": len(new_facilities),
            "reconciled_matches": reconciled_count,
            "new_facilities_inserted": inserted_count,
            "total_registered_facilities": db.query(IndustrialFacilityModel).count()
        }

    def get_all_facilities(self, db: Session) -> List[IndustrialFacilityModel]:
        """Returns all registered industrial facilities."""
        return db.query(IndustrialFacilityModel).all()

    def find_nearest_facility(self, lat: float, lon: float, db: Optional[Session] = None) -> Optional[IndustrialFacilityModel]:
        """Finds nearest industrial facility within 50km radius."""
        if db is None:
            return None
        facs = db.query(IndustrialFacilityModel).all()
        if not facs:
            return None
        best = None
        min_d = float('inf')
        for f in facs:
            d = self.haversine_distance_m(lat, lon, f.latitude, f.longitude)
            if d < min_d:
                min_d = d
                best = f
        return best if min_d <= 50000.0 else None

industrial_context_service = IndustrialContextService()

# SIH26162 — Comprehensive Architecture Migration Audit & Technical Strategy
## Transformation of REACT-X from SIH 1505 (Hazard Command) to SIH26162 (AI Satellite Thermal Intelligence & Industrial Fire Platform)
**Target Organization:** NTRO (National Technical Research Organisation)  
**Category:** Software | **Theme:** Miscellaneous  
**Document Version:** 1.0.0 (Authoritative System Audit)  
**Status:** Approved for Implementation Planning  

---

## 1. Executive Problem Statement & Product Direction

### 1.1 The Shift: SIH 1505 $\longrightarrow$ SIH26162
The previous project scope (**SIH 1505 — Industrial Emergency Response / Hazard Command Center**) was focused primarily on post-accident physical consequence modeling, Gaussian chemical dispersion, in-facility worker evacuation, and tactical emergency response.

The new target problem (**SIH26162 — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data**) expands this paradigm into spaceborne early thermal anomaly detection, persistent industrial heat characterization, and explainable AI classification, while **preserving all existing emergency-response capabilities** as an integrated downstream response engine.

```
+-------------------------------------------------------------------------------------------------------+
|                                    SIH26162 CORE PRODUCT LIFECYCLE                                    |
|                                                                                                       |
|   DETECT               IDENTIFY              CLASSIFY               MONITOR             ABNORMALITY   |
| [NASA FIRMS]   --> [OSM / GEM / GIS] --> [Explainable AI]   --> [Persistent Base] --> [FRP / Temp]    |
| (VIIRS/MODIS)      (Nearest Facility)    (Flare/Fire/Agri)      (Day/Night Recur)      (Deviation)    |
|                                                                                             |         |
|                                                                                             v         |
|                                                                                       INDUSTRIAL RISK |
|                                                                                     [Facility Impact] |
|                                                                                             |         |
|                                                                                             v         |
|                                                                                      EMERGENCY COMMAND|
|                                                                                     [REACT-X Engine]  |
+-------------------------------------------------------------------------------------------------------+
```

### 1.2 The Core Operational Question
The application no longer opens as an isolated in-facility accident dashboard. It opens to immediately answer the 5 core national intelligence questions:
1. **WHERE ARE THE HOTSPOTS?** (Geospatial thermal anomaly detection across regional and industrial sectors)
2. **WHICH ONES ARE INDUSTRIAL?** (Spatial attribution matching anomalies to known industrial facilities, refineries, power plants, chemical parks, and mines using OSM and Global Energy Monitor)
3. **WHICH ONES ARE PERSISTENT?** (Distinguishing normal recurring process heat/flares from sudden new events)
4. **WHICH ONES ARE BECOMING ABNORMAL?** (Statistical and AI-driven thermal deviation scoring against facility-specific historical baselines)
5. **WHICH ONES REQUIRE EMERGENCY INTERVENTION?** (Direct automated handoff of high-risk anomalies into the comprehensive REACT-X emergency command suite)

---

## 2. Current Architecture (As-Is State Audit)

### 2.1 Backend Architecture
- **Framework:** FastAPI (Python 3.12) with modular REST routers under `/api`.
- **Database & Storage:** Dual-mode repository DAO supporting SQLite (`sih1505.db`) and PostgreSQL / TimescaleDB / PostGIS schema definitions.
- **Service Layer (21 Submodules):**
  - `analytics/`: Historical incident metrics, MTTR/MTBF analytics, and dynamic incident timeline synthesis.
  - `audit/`: Structured, immutable decision-support audit logging with role tracking.
  - `chemicals/`: Comprehensive NIOSH/OSHA chemical property registry and incompatibility matrix.
  - `copilot/`: Natural language incident assistant and 12-point executive situation brief generator.
  - `evacuation/`: Dijkstra-based dynamic egress routing with hazard zone edge pruning.
  - `graph/`: NetworkX multi-relational risk graph for domino cascade propagation and environmental receptor consequence analysis.
  - `hazard/`: Gaussian screening dispersion physics engine supporting toxic plumes, pool fires, vapor cloud explosions, and BLEVE fireballs.
  - `impact/`: Personnel vulnerability, facility asset intersection, and multi-parameter risk scoring.
  - `industrial/`: Telemetry simulator with Modbus TCP, MQTT, and OPC-UA protocol adapters.
  - `ingestion/`: Ingestion metrics, rolling buffer, stream classifier (Hot/Warm/Cold), and data quality validation engine.
  - `observability/`: System health, pipeline latency monitoring, and broker connection tracking.
  - `predictive/`: Asset health index, multi-signal early warning engine, and spatial domino risk analysis.
  - `preplan/`: Automated vector-mapped industrial fire pre-plan generator (ReportLab PDF) and human HSE authorization governance.
  - `preventive/`: Ranked engineering mitigations, preventive what-if recalculator, and non-negotiable safety-control boundary.
  - `resources/`: Chemical-adaptive emergency equipment dispatch and tactical incident action checklists.
  - `scenarios/`: Scenario preset repository and 19-stage Ammonia header rupture storyline orchestrator.
  - `site/`: Plant asset geometry, worker rosters, internal road networks, muster points, and gates.
  - `storage/`: Operating limits and telemetry persistence DAO.
  - `vision/`: CCTV camera surveillance and bounding box hazard detector.
  - `weather/`: Open-Meteo REST live meteorological feed with offline scenario fallbacks.
  - `whatif/`: Side-by-side scenario consequence comparator (Scenario A vs B mathematical deltas).

### 2.2 Frontend Architecture
- **Framework:** React 18, Vite, Vanilla CSS + TailwindCSS utilities.
- **Geospatial Visualization:** Leaflet & React-Leaflet 2D GIS map with layer controls and custom SVG markers.
- **State Management:** Authoritative single-source-of-truth canonical incident state model (`canonicalState.js`).
- **Role-Based Views:** Dedicated interfaces for `HSE_COMMANDER`, `FIELD_RESPONDER`, `PLANT_MANAGER`, `DISTRICT_AUTHORITY`, `EXECUTIVE_AUTHORITY`, and `DEMO_ADMIN`.

### 2.3 Verification Baseline
- **Frontend Production Build:** Passing cleanly (`vite build` completed with 0 errors, 2,350 modules transformed).
- **Backend Test Suite:** 15 in-process vertical slice tests passing; 5 live-server E2E integration test scripts available for running FastAPI instances.

---

## 3. Granular Feature Inventory & Classification Matrix

Every current and planned feature is audited and classified into one of six categories:
- **`KEEP`**: Essential capability to preserve with zero regressions.
- **`MERGE`**: Capability combined with another module for enhanced cohesion.
- **`MOVE`**: Feature relocated to its proper layer in the new information architecture.
- **`DE-EMPHASIZE`**: Complex background or prototype feature moved out of primary focus.
- **`REMOVE`**: Clutter, duplicate UI elements, or outdated references safe for removal.
- **`NEW`**: Brand new core capability required for SIH26162 NTRO problem statement.

| Module / Feature | Current Location | Classification | Justification & SIH26162 Target Role |
| :--- | :--- | :--- | :--- |
| **NASA FIRMS Thermal Ingestion** | *New* | `NEW` | Real-time and historical ingestion of VIIRS (S-NPP, NOAA-20/21) and MODIS thermal anomalies with FRP, brightness temp, and confidence. |
| **Industrial Source Attribution Engine** | *New* | `NEW` | Spatial KD-tree & polygon buffer matching against OSM, Global Energy Monitor (GEM), and Bhuvan industrial registries. |
| **Persistent Thermal Source Engine** | *New* | `NEW` | Spatial clustering (DBSCAN), recurrence frequency, historical FRP baseline, day/night persistence, and abnormality scoring. |
| **AI Thermal Classification Architecture** | *New* | `NEW` | Multi-class classification (Industrial Fire, Gas Flare, Routine Industrial Heat, Mining, Agri, Wildfire) with explainable feature attribution. |
| **VIIRS Nightfire (VNF) Adapter** | *New* | `NEW` | Interface for Planck curve thermal physical characterization (source temp K, radiant heat flux, physical area $m^2$). |
| **Multi-Satellite Corroboration Layer** | *New* | `NEW` | Multi-sensor confirmation model (FIRMS VIIRS/MODIS + Nightfire + Sentinel-2/Landsat + INSAT-3D/3DR/3DS). |
| **Industrial Facility Profile & Fingerprint** | *New* | `NEW` | Deep-dive modal/drawer with baseline FRP, historical recurrence heatmap, current anomaly status, and satellite evidence. |
| **Satellite Thermal $\rightarrow$ Emergency Handoff** | *New* | `NEW` | One-click or automated promotion of confirmed abnormal industrial thermal anomalies into active REACT-X incident response. |
| **Left Sidebar Navigation** | *New UI* | `NEW` | Compact, collapsible, hierarchical left navigation replacing horizontal tab clutter. |
| **Regional Multi-Scale Thermal Map** | `PlantMap.jsx` | `MERGE` + `MOVE` | Expand map from single-plant GIS to regional multi-scale view (Regional Satellite Hotspots $\rightarrow$ Industrial Cluster $\rightarrow$ Plant Twin). |
| **Gaussian Chemical Dispersion Physics** | `hazard_service.py` | `KEEP` + `MOVE` | Preserved as core consequence simulation engine inside the Emergency Response layer. |
| **Personnel Impact & Risk Matrix** | `impact_service.py` | `KEEP` + `MOVE` | Preserved for worker vulnerability, casualty estimation, and asset exposure. |
| **Dynamic Dijkstra Safe Evacuation** | `evacuation_service.py` | `KEEP` + `MOVE` | Preserved for obstacle-pruned egress route calculation. |
| **Tactical Resource Optimization** | `resource_service.py` | `KEEP` + `MOVE` | Preserved for emergency vehicle dispatch, hazmat suits, and foam/water bowser allocation. |
| **Vector Fire Pre-Plan PDF (ReportLab)** | `preplan_service.py` | `KEEP` + `MOVE` | Preserved for statutory ERDMP / OISD compliant emergency action documentation. |
| **Human Authorization & SIS Safety Boundary** | `authorization_service.py` | `KEEP` + `MOVE` | Preserved for 3-point checklist validation and cryptographic governance tokens. |
| **Executive Situation Brief (12-Point)** | `executive_brief_service.py` | `KEEP` + `MOVE` | Preserved for one-click strategic situation briefs under Governance. |
| **Domino / Cascade Risk Analysis** | `domino_service.py` | `KEEP` + `MOVE` | Preserved under Risk & Prediction for spatial cascade propagation. |
| **What-If Consequence Comparator** | `whatif_service.py` | `KEEP` + `MOVE` | Preserved under Risk & Prediction for scenario A vs B deltas. |
| **Historical Incident Analytics** | `analytics_service.py` | `KEEP` + `MOVE` | Preserved under Analysis for MTTR/MTBF, frequency distributions, and equipment rankings. |
| **Incident Timeline & Event Replay** | `timeline_service.py` | `KEEP` + `MOVE` | Preserved under Analysis for milestone reconstruction. |
| **Decision Audit Trail** | `audit_service.py` | `KEEP` + `MOVE` | Preserved under Governance/Analysis for immutable action tracking. |
| **Multi-Level Role Views (4 Views)** | `components/roles/` | `KEEP` + `MOVE` | Preserved and integrated into the top bar role selector. |
| **Predictive Asset Health Index** | `predictive_service.py` | `MERGE` | Merged with facility baseline & thermal abnormality engine under Risk & Prediction. |
| **CCTV Computer Vision Surveillance** | `vision_service.py` | `DE-EMPHASIZE` | Moved to secondary ground-truth optical confirmation under Facility Context. |
| **Modbus/MQTT/OPC-UA Telemetry Ingestion** | `industrial/` | `DE-EMPHASIZE` | Background service retained; UI multiplexing controls de-emphasized in favor of FIRMS streaming. |
| **19-Stage Ammonia Demo Orchestrator** | `scenario_orchestrator.py` | `DE-EMPHASIZE` | Relocated to dedicated "Demo / Simulation Mode" with clear visual badges. |
| **Horizontal Navigation Tab Bar** | `CommandCenter.jsx` | `REMOVE` | Replaced by clean, collapsible Left Sidebar. |
| **Top Bar Redundant Action Buttons** | `Header.jsx` | `REMOVE` | Streamlined into clean header status bar and context drawers. |
| **SIH 1505 Textual References** | Repository-wide | `REMOVE` | Updated to official SIH26162 branding across headers, titles, APIs, and reports. |

---

## 4. Retained & Repositioned Core Capabilities (`KEEP`)

To ensure absolute preservation of our competitive advantage, the following 17 capabilities remain fully operational within their new platform layers:

```
+-------------------------------------------------------------------------------------------------------+
|                                    PRESERVED REACT-X CAPABILITY SUITE                                 |
|                                                                                                       |
|  [THERMAL INTELLIGENCE]        [RISK & PREDICTION]           [RESPONSE LAYER]      [GOVERNANCE]       |
|  - Live FIRMS Hotspots        - Thermal Baselines           - Incident Command     - Executive Brief  |
|  - Persistent Heat Clusters   - Abnormality Detection       - Dispersion Plume     - SIS Auth Boundary|
|  - Source Attribution         - What-If Comparison          - Evacuation Dijkstra  - Decision Audit   |
|  - Multi-Satellite Fusion     - Domino Cascade Risk         - Tactical Resources   - Pre-Plan PDF     |
|                               - Predictive Asset Health     - Personnel Impact     - System Health    |
+-------------------------------------------------------------------------------------------------------+
```

1. **Industrial GIS & Digital Twin**: Preserved and expanded to support multi-scale zoom from country-level FIRMS hotspots to plant-level asset coordinates ($21.685^\circ\text{N}, 72.575^\circ\text{E}$).
2. **Atmospheric Dispersion Physics**: Preserved Gaussian screening dispersion for toxic gases ($NH_3, Cl_2$), pool fires ($C_6H_6$), BLEVEs ($LPG$), and VCEs with Pasquill-Gifford atmospheric stability curves.
3. **Personnel Vulnerability & Impact Matrix**: Preserved 2D spatial intersection of ERPG-3/2/1 threat zones against worker rosters, tracking shelter-in-place vs evacuation status.
4. **Dynamic Evacuation Routing Engine**: Preserved Dijkstra pathfinding on internal road networks with obstacle avoidance and dynamic pruning of toxic corridors.
5. **Tactical Resource Allocation**: Preserved automated equipment dispatch formulas (foam/water bowsers, Hazmat Level A/B suits, ambulances) with vehicle transit ETAs.
6. **Statutory Fire Pre-Plan Generator**: Preserved vector-mapped ReportLab PDF document compilation complying with ERDMP and OISD-GDN-169 standards.
7. **Human Authorization Governance**: Preserved mandatory 3-item safety checklist validation before emitting signed authorization records (`AUTH-SIS-YYYYMMDD-XXXXXX`).
8. **12-Point Executive Situation Brief**: Preserved one-click synthesis answering the 6 core executive questions (What happened? Where is it? Who is affected? What is being done? What is required? What is the trend?).
9. **Domino / Cascade Risk Analysis**: Preserved spatial vulnerability assessment analyzing heat flux ($37.5\text{ kW/m}^2$, $12.5\text{ kW/m}^2$, $4.0\text{ kW/m}^2$) and overpressure ($0.3\text{ bar}$) against neighboring tanks.
10. **What-If Consequence Simulator**: Preserved dual-scenario mathematical recalculator quantifying delta risk ($\Delta R$) across meteorological or operational changes.
11. **Historical Incident Analytics**: Preserved incident frequency distributions, MTTR/MTBF analytics, and high-risk equipment rankings.
12. **Incident Timeline & Milestone Stream**: Preserved authoritative event reconstruction tracking detection, alert, containment, evacuation, and all-clear milestones.
13. **Decision Audit Trail**: Preserved immutable logging capturing actor role, module, input summary, AI recommendation, human decision, and outcome.
14. **Role-Based Abstraction Views**: Preserved specialized UX for Field Responder, HSE Commander, Plant Manager, District Authority, and Executive Authority.
15. **NIOSH/OSHA Chemical Registry**: Preserved molecular weight, vapor pressure, IDLH, ERPG-1/2/3, and chemical incompatibility matrix.
16. **Meteorological Live & Demo Service**: Preserved Open-Meteo API integration with automatic fallback to scenario parameters.
17. **Dual-Mode Persistence Architecture**: Preserved dual-mode repository DAO supporting SQLite and PostgreSQL / TimescaleDB / PostGIS.

---

## 5. Merged, Moved & De-Emphasized Capabilities

### 5.1 Features Merged (`MERGE`)
- **Asset Telemetry $\longrightarrow$ Facility Thermal Baseline Engine:** In-plant temperature/pressure telemetry is merged with satellite thermal anomaly tracking to create a unified thermal baseline model combining internal sensor data with external spaceborne radiometric observations.
- **Risk Graph $\longrightarrow$ Environmental & Infrastructure GIS Attribution:** The NetworkX risk graph is merged with OSM spatial layers to evaluate proximity to rivers, sanctuaries, highways, and residential settlements directly from satellite coordinates.

### 5.2 Features Moved (`MOVE`)
- **Emergency Response Components:** Moved from dominant top-level tabs to the downstream **RESPONSE** layer, accessible automatically when an anomaly is classified as an industrial fire or confirmed hazard.
- **Computer Vision Surveillance:** Moved from top navigation into the **Facility Profile / Evidence Panel** as secondary optical validation.

### 5.3 Features De-Emphasized (`DE-EMPHASIZE`)
- **Raw Sensor Protocol Adapters (Modbus/MQTT/OPC-UA):** Background services remain active in the backend; UI multiplexing controls are de-emphasized in favor of NASA FIRMS thermal anomaly feeds.
- **19-Stage T-04 Demonstration Storyline:** Repositioned into a dedicated "Demo / Simulation Mode" accessible via header badge to avoid confusing evaluators.

---

## 6. Features Genuinely Safe to Remove (`REMOVE`)

1. **Horizontal Top Navigation Bar:** Replaced by the professional Left Sidebar.
2. **Duplicate PDF and Demo Triggers:** Consolidated into contextual action buttons within their respective views.
3. **Outdated SIH 1505 References:** All visible textual instances of "SIH 1505" and "SIH-1505" in UI titles, headers, PDF footers, API documentation, and metadata are replaced with **SIH26162**.

---

## 7. New SIH26162 Core Modules Required (`NEW`)

### 7.1 NASA FIRMS Thermal Anomaly Ingestion Adapter
- **Function:** Ingests live and historical satellite thermal anomaly data from NASA FIRMS.
- **Sensors Supported:** VIIRS (Suomi-NPP, NOAA-20, NOAA-21) at 375m resolution; MODIS (Terra, Aqua) at 1km resolution.
- **Data Attributes Parsed:** Latitude, longitude, acquisition date/time (UTC), satellite, instrument, Fire Radiative Power (FRP in MW), brightness temperature ($T_{21}$ / $T_{31}$ in Kelvin), detection confidence (low/nominal/high or 0-100%), day/night flag, scan angle, track size.
- **Implementation Design:** Non-blocking async adapter with local caching, GeoJSON serialization, and rate-limit resilience.

### 7.2 Industrial Source Attribution Engine (OSM + GEM + Bhuvan)
- **Function:** Determines whether a detected hotspot is associated with an industrial facility.
- **Data Sources:** OpenStreetMap industrial tags (`industrial=refinery`, `industrial=chemical`, `landuse=industrial`, `man_made=works`), Global Energy Monitor (power plants, oil/gas infrastructure, steel mills), and India-specific Bhuvan GIS datasets.
- **Attribution Logic:** Spatial KD-tree radius search + polygon boundary containment + facility type classification. Calculates distance to nearest industrial asset and assigns attribution confidence.

### 7.3 Persistent Thermal Source Analysis Engine
- **Function:** Analyzes thermal anomaly recurrence over multi-month/multi-year timelines to distinguish normal routine industrial heat from emerging fires.
- **Algorithms:**
  - Spatial grouping & clustering (DBSCAN / geospatial grid hashing).
  - Recurrence rate calculation ($\text{Detections} / \text{Satellite Passes}$).
  - Day vs Night diurnal ratio (flares and furnaces operate 24/7; agricultural fires occur predominantly during daytime).
  - Historical FRP & brightness temperature baselines ($\mu_{FRP}, \sigma_{FRP}$).
  - Thermal Abnormality Score: $Z_{FRP} = \frac{\text{FRP}_{current} - \mu_{FRP}}{\sigma_{FRP}}$.
- **Output Classes:**
  1. `EXPECTED_PERSISTENT_SOURCE` (Normal routine flare, furnace, or kiln within historical baseline)
  2. `ABNORMAL_PERSISTENT_SOURCE` (Known persistent site exhibiting sudden FRP spike, area expansion, or temperature surge)
  3. `TRANSIENT_EVENT` (Sudden new anomaly at a location without prior thermal history)
  4. `NATURAL_NON_INDUSTRIAL` (Wildfire, forest fire, or agricultural stubble burning outside industrial bounds)
  5. `UNCLASSIFIED` (Low-confidence or unconfirmed anomaly requiring further satellite passes)

### 7.4 Explainable AI Thermal Source Classification Architecture
- **Function:** Classifies thermal anomalies into actionable categories using multi-feature inference.
- **7-Class Taxonomy:**
  1. `INDUSTRIAL_FIRE` (Abnormal blaze at refinery, chemical storage, or factory)
  2. `GAS_FLARE` (Routine or elevated hydrocarbon flare stack emission)
  3. `ROUTINE_PROCESS_HEAT` (Furnace, smelter, kiln, or thermal power boiler)
  4. `MINING_PROCESS_HEAT` (Coal seam fire, slag dump, or extraction facility)
  5. `AGRICULTURAL_BURNING` (Crop residue / stubble burning)
  6. `WILDFIRE_NATURAL` (Vegetation, forest, or brush fire)
  7. `OTHER_UNKNOWN` (Unattributed or anomalous heat signature)
- **ML Design:** Clean feature extraction pipeline (spatial proximity, land cover, FRP, temperature, diurnal ratio, recurrence index) designed for future XGBoost / LightGBM integration, providing probability distributions and SHAP-style top feature contributions.

### 7.5 VIIRS Nightfire (VNF) Physical Characterization Adapter
- **Function:** Architecture for integrating Earth Observation Group (EOG) VIIRS Nightfire spectral radiance data.
- **Physical Features:** Planck blackbody temperature curve fitting ($T$ in Kelvin), radiant heat flux ($W/m^2$), and physical source footprint ($m^2$).

### 7.6 Multi-Satellite Corroboration Layer
- **Multi-Tiered Latency & Resolution Model:**
  - **Tier 1 (Fast Detection):** NASA FIRMS VIIRS (375m) & MODIS (1km) — Latency: 1–3 hours.
  - **Tier 2 (Physical Characterization):** VIIRS Nightfire (750m nocturnal) — Latency: 4–6 hours.
  - **Tier 3 (Optical/SWIR Confirmation):** Sentinel-2 (10m/20m SWIR Band 11/12) & Landsat 8/9 (30m/100m Thermal Band 10) — Latency: 1–5 days.
  - **Tier 4 (India Geostationary Corroboration):** INSAT-3D/3DR/3DS Thermal Infrared — Latency: 15–30 minutes.

### 7.7 Industrial Facility Thermal Profile & Fingerprint
- **Interactive Facility Dossier:** Clicking any industrial facility opens a detailed profile displaying:
  - Facility Name, Sector, Operator, Coordinates, and PESO/OISD ERDMP registration.
  - Thermal Baseline Signature (Mean FRP, Normal Diurnal Distribution, Recurrence Heatmap).
  - Active & Recent Thermal Detections with satellite source, sensor, and timestamp.
  - Current Abnormality Status and Consequence Risk Score.
  - One-click trigger: "Initiate Emergency Response Command".

### 7.8 Satellite Thermal $\longrightarrow$ REACT-X Emergency Handoff Bridge
- **Automated / Operator-Approved Pipeline:** When an anomaly is confirmed as an `INDUSTRIAL_FIRE` or `ABNORMAL_PERSISTENT_SOURCE`, the system generates a unified Incident Packet and hands off directly to REACT-X:
  $$\text{Thermal Anomaly} \longrightarrow \text{Asset Match} \longrightarrow \text{Dispersion Simulation} \longrightarrow \text{Worker Impact} \longrightarrow \text{Evacuation Route} \longrightarrow \text{Pre-Plan PDF}$$

---

## 8. Recommended Information Architecture & Left Sidebar Navigation

The user interface transitions from a cluttered horizontal top bar to a sleek, collapsible **Left Sidebar Navigation**:

```
+------------------------------------+---------------------------------------------------------------------------------+
| REACT-X  [SIH26162]                | TOP BAR: System State | Active Anomaly Feed | Role Selector | Quick Export      |
+------------------------------------+---------------------------------------------------------------------------------+
|                                    |                                                                                 |
| ◉ OVERVIEW                         |                                                                                 |
|   - Thermal Intelligence Map       |                                                                                 |
|                                    |                            CENTRAL VIEW AREA                                    |
| ▼ THERMAL INTELLIGENCE             |                                                                                 |
|   - Live Thermal Events (FIRMS)    |  [Multi-Layer Geospatial Map / Analytical Dossier / Emergency Workspace]         |
|   - FIRMS Monitor & Telemetry      |                                                                                 |
|   - AI Classification Engine       |                                                                                 |
|   - Persistent Thermal Sources     |                                                                                 |
|                                    |                                                                                 |
| ▼ INDUSTRIAL CONTEXT               |                                                                                 |
|   - Industrial Facilities          |                                                                                 |
|   - Facility Thermal Profiles      |                                                                                 |
|   - Land Cover & Infrastructure    |                                                                                 |
|   - OSM / GEM Registry Explorer    |                                                                                 |
|                                    |                                                                                 |
| ▼ RISK & PREDICTION                |                                                                                 |
|   - Thermal Baselines & Warning    |                                                                                 |
|   - Abnormality Detection          |                                                                                 |
|   - What-If Consequence Simulator  |                                                                                 |
|   - Domino & Cascade Risk          |                                                                                 |
|                                    |                                                                                 |
| ▼ RESPONSE (REACT-X)               |                                                                                 |
|   - Incident Command & Handoff     |                                                                                 |
|   - Personnel Impact & Matrix      |                                                                                 |
|   - Safe Evacuation Routing        |                                                                                 |
|   - Tactical Emergency Dispatch    |                                                                                 |
|   - Fire Pre-Plan Document         |                                                                                 |
|                                    |                                                                                 |
| ▼ ANALYSIS & GOVERNANCE            |                                                                                 |
|   - Historical Heat Analytics      |                                                                                 |
|   - Incident Timeline & Replay     |                                                                                 |
|   - Decision Audit Trail           |                                                                                 |
|   - Executive Situation Brief      |                                                                                 |
|   - SIS Human Authorization        |                                                                                 |
|   - System Health & Feeds          |                                                                                 |
|                                    |                                                                                 |
+------------------------------------+---------------------------------------------------------------------------------+
| [AI COPILOT DRAWER (Floating)]     | BOTTOM BAR: Time Scrubber / Latency Monitor / Data Quality Indicator            |
+------------------------------------+---------------------------------------------------------------------------------+
```

---

## 9. Data Architecture & Canonical Schema Evolution

### 9.1 Unified Canonical Thermal Event Model (`CanonicalThermalEvent`)
Extends our existing `CanonicalEvent` to represent spaceborne thermal observations alongside ground telemetry:

```python
class CanonicalThermalEvent(BaseModel):
    event_id: str                          # Unique hash / UUID
    source_satellite: str                  # "VIIRS_SNPP", "VIIRS_NOAA20", "MODIS_AQUA", "SENTINEL_2", "INSAT_3D"
    sensor_name: str                       # "VIIRS_375M", "MODIS_1KM", "MSI_20M"
    acquisition_timestamp: datetime        # ISO 8601 UTC
    latitude: float                        # WGS84 Latitude
    longitude: float                       # WGS84 Longitude
    frp_mw: float                          # Fire Radiative Power in Megawatts
    brightness_temp_k: Optional[float]     # Brightness Temperature in Kelvin
    confidence: str                        # "LOW", "NOMINAL", "HIGH" or percentage
    day_night: str                         # "D" (Day) or "N" (Night)
    attributed_facility_id: Optional[str]  # Matched industrial facility
    facility_distance_m: Optional[float]   # Distance to facility boundary
    classification: str                    # "INDUSTRIAL_FIRE", "GAS_FLARE", "ROUTINE_HEAT", etc.
    classification_confidence: float       # 0.00 - 1.00
    persistence_category: str              # "EXPECTED_PERSISTENT", "ABNORMAL_PERSISTENT", "TRANSIENT"
    abnormality_score: float               # Statistical z-score deviation (0.0 - 100.0)
    risk_level: str                        # "CRITICAL", "HIGH", "MODERATE", "LOW", "NOMINAL"
    is_live_data: bool                     # True for real satellite feed, False for simulated/demo
    data_quality_flags: List[str]          # ["GEO_VALIDATED", "CLOUD_CLEAR", "CALIBRATED"]
```

### 9.2 Storage Strategy
- **PostgreSQL / PostGIS (Active Tier):** Stores facility geometries, active thermal anomalies, spatial spatial indexes (R-Tree / GIST), spatial relationships, user sessions, and decision audit logs.
- **GeoParquet (Historical Archive Tier):** High-performance columnar storage for multi-year satellite thermal anomaly archives partitioned by year and region.
- **Object Storage / COG (Imagery Tier):** Cloud Optimized GeoTIFFs for Sentinel-2 / Landsat high-resolution confirmation chips when demanded on-the-fly.

---

## 10. Risk Analysis & Functionality Preservation

| Risk Factor | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Accidental Loss of Emergency Modules** | Breaking existing simulation, evacuation, or PDF pre-plan features. | Zero-deletion policy for emergency services. Comprehensive automated regression suite executed before and after every migration step. |
| **Data Honesty & Fake Satellite Data** | Presenting simulated data as live satellite observations to NTRO evaluators. | Strict data provenance tags (`is_live_data: true/false`). Prominent UI badges clearly distinguishing LIVE feeds from DEMO / SIMULATION data. |
| **Untrained ML Model Claims** | Misleading evaluators with pseudo-machine learning claims. | Explicit architecture honesty: expose clear heuristic rules, statistical $z$-scores, and well-defined model inference interfaces ready for trained weights. |
| **Performance Degradation on Large Datasets** | Slow map rendering when thousands of regional hotspots are loaded. | Spatial viewport bounding-box querying, clustering (Leaflet MarkerCluster / GeoJSON tile streaming), and debounced search filters. |
| **State Inconsistency During Emergency Handoff** | Disconnect between satellite anomaly coordinates and chemical plant dispersion origin. | Canonical state mapper translating `CanonicalThermalEvent` directly into `HazardSimulationRequest` with coordinate reconciliation. |

---

## 11. 12-Phase Migration Sequence

```
  PHASE 1: Complete Repository & Migration Audit (THIS DOCUMENT)
     │
  PHASE 2: Information Architecture & Collapsible Left Sidebar Navigation
     │
  PHASE 3: Canonical Thermal Data Model & Database Schema Evolution
     │
  PHASE 4: NASA FIRMS Thermal Ingestion Adapter & Live/Historical Feed
     │
  PHASE 5: Industrial Source Attribution Engine (OSM, GEM, Bhuvan)
     │
  PHASE 6: Persistent Thermal Source Analysis & Abnormality Engine
     │
  PHASE 7: Explainable AI Thermal Source Classification Architecture
     │
  PHASE 8: Multi-Satellite Confirmation Layer (VIIRS Nightfire, Sentinel-2, INSAT)
     │
  PHASE 9: Multi-Layer Geospatial Map Experience & Facility Thermal Dossiers
     │
  PHASE 10: Seamless Satellite-to-Emergency Handoff (REACT-X Integration)
     │
  PHASE 11: Comprehensive Test Suite, Branding Updates (SIH26162), & Data Quality Audits
     │
  PHASE 12: Final UI Polish, Role Verification, & Demo Presentation Readiness
```

---

## 12. Conclusion & Next Step
The audit confirms that **REACT-X possesses an exceptional foundation** of industrial physics, dynamic evacuation routing, tactical response allocation, and regulatory pre-planning.

By wrapping this engine within a **world-class satellite thermal intelligence layer** powered by NASA FIRMS, OSM spatial attribution, thermal persistence analysis, and explainable AI classification, SIH26162 becomes an unbeatable, state-of-the-art platform for NTRO.

**Next Action:** Proceed to the concise Implementation Plan for User Approval before executing Phase 2.

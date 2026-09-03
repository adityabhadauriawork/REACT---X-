# ⚡ REACT-X — AI Satellite Thermal Intelligence & Industrial Fire Platform
### SIH26162 • National Technical Research Organisation (NTRO) • Smart India Hackathon 2026
**Official Problem Statement:** *AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data*

![Platform Status](https://img.shields.io/badge/Status-SIH26162%20Production%20Grade-06b6d4?style=for-the-badge)
![Target Organization](https://img.shields.io/badge/Target-NTRO%20Intelligence-4f46e5?style=for-the-badge)
![Lifecycle](https://img.shields.io/badge/Lifecycle-Detect%20%E2%86%92%20Classify%20%E2%86%92%20Monitor%20%E2%86%92%20Respond-10b981?style=for-the-badge)
![Safety Boundary](https://img.shields.io/badge/Safety%20Boundary-Strict%20Read--Only%20OT-f59e0b?style=for-the-badge)

---

## 🎯 Executive Product Vision

The new primary product story is:
$$\textbf{DETECT} \longrightarrow \textbf{IDENTIFY} \longrightarrow \textbf{CLASSIFY} \longrightarrow \textbf{MONITOR} \longrightarrow \textbf{DETECT ABNORMALITY} \longrightarrow \textbf{ASSESS RISK} \longrightarrow \textbf{EMERGENCY RESPONSE}$$

**Primary Core Question:**  
*"What is this thermal anomaly, where is it, why is it there, is it normal, and is it becoming abnormal?"*

### Core Operational Questions Answered:
1. **WHERE ARE THE HOTSPOTS?** (Geospatial NASA FIRMS VIIRS/MODIS thermal anomaly ingestion across regional industrial corridors).
2. **WHICH ONES ARE INDUSTRIAL?** (Spatial attribution matching anomalies to known industrial facilities, refineries, power plants, chemical parks, and mines using OSM and Global Energy Monitor).
3. **WHICH ONES ARE PERSISTENT?** (Distinguishing normal recurring process heat/flares from sudden emerging fire events using multi-month recurrence baselines).
4. **WHICH ONES ARE BECOMING ABNORMAL?** (Statistical and AI-driven thermal deviation scoring against facility-specific historical baselines $Z_{FRP}$).
5. **WHAT IS THE NATURE OF THE SOURCE?** (Explainable AI classification across the 7-class taxonomy: *Industrial Fire, Gas Flare, Routine Process Heat, Mining Heat, Agricultural Burning, Wildfire, Other*).
6. **WHAT ARE THE PHYSICAL CHARACTERISTICS?** (VIIRS Nightfire Planck curve source temperature in Kelvin, radiant heat flux $W/m^2$, and physical source footprint $m^2$).
7. **HOW IS IT CORROBORATED?** (Multi-sensor corroboration combining FIRMS, Nightfire, Sentinel-2 SWIR, Landsat-9 Thermal, and INSAT-3DR rapid geostationary scans).
8. **IF A FIRE IS CONFIRMED, HOW DOES EMERGENCY COMMAND ENGAGE?** (Direct automated handoff to the complete REACT-X emergency command suite: Gaussian screening dispersion, worker impact matrix, dynamic Dijkstra safe evacuation routing, tactical resource dispatch, and statutory ERDMP/OISD Fire Pre-Plan PDF generation).

---

## 🏛️ System Architecture

```
+-----------------------------------------------------------------------------------+
|                                 FIELD OT LAYER                                    |
|   Pressure Transmitters • RTD Temp • Vibration Probes • Acoustic Sniffers • CCTV  |
+------------------------------------------+----------------------------------------+
                                           | Multiplexed Physical Streams
+------------------------------------------v----------------------------------------+
|                          EDGE GATEWAYS & PROTOCOL ADAPTERS                        |
|               [OPC UA Client]    [MQTT Backbone]    [Modbus TCP Poller]           |
+------------------------------------------+----------------------------------------+
                                           | Normalized Payloads
+------------------------------------------v----------------------------------------+
|                                DATA QUALITY ENGINE                                |
|  - Timestamp validation (-30s future / +30s timeout)                              |
|  - Range boundary & Physical plausibility checks                                  |
|  - Impossible rate-of-change spike rejection                                      |
|  - Duplicate sequence suppression                                                 |
|  - Quality Tagging: [GOOD] [UNCERTAIN] [BAD] [STALE]                              |
+------------------------------------------+----------------------------------------+
                                           | CanonicalEvent Model
+------------------------------------------v----------------------------------------+
|                       DECISION-VALUE STREAM CLASSIFIER                            |
|                                                                                   |
|      +-----------------------+   +-----------------------+   +-----------------+  |
|      |       HOT PATH        |   |       WARM PATH       |   |    COLD PATH    |  |
|      | - 0-10s Latency       |   | - 1m/5m/15m Trends    |   | - 30d+ Archive  |  |
|      | - Multi-Signal Fusion |   | - Rolling Aggregates  |   | - Model Training|  |
|      | - Anomaly Scoring     |   | - Telemetry Baseline  |   | - Turnaround    |  |
|      | - Early Warning State |   | - In-Memory Deque     |   | - Regulatory    |  |
|      +-----------+-----------+   +-----------+-----------+   +--------+--------+  |
+------------------|---------------------------|------------------------|-----------+
                   |                           |                        |
+------------------v---------------------------v------------------------v-----------+
|                          STORAGE ARCHITECTURE (Dual-Mode)                         |
|  - PostgreSQL / SQLite: Relational Assets, Chemicals, Limits, Incident Packets    |
|  - PostGIS: Spatial Boundaries, Vulnerable Communities, Water Bodies, Evac Paths  |
|  - TimescaleDB: Partitioned Hypertables with 2-day Compression & 30-day Retention |
|  - Object Storage / MinIO: Thermal Radiometric Frames, Pre-Plan PDFs, Evidence    |
+-----------------------------------------------------------------------------------+
```

---

## 🚀 Key Modules & Capabilities

### 1. Pre-Incident Safety Center & Early Warning
- **Multi-Signal Evidence Fusion**: Fuses 5 distinct physical channels (Mechanical Vibration RMS, Thermal Excursions, Operating Pressure, Ultrasonic Acoustic Leaks, and Turnaround Overdue Aging).
- **Hybrid Anomaly Detection**: Layer 1 Deterministic Limits + Layer 2 Statistical Z-Score + Layer 3 Multivariate Machine Learning (*Isolation Forest*).
- **State Progression**: `NORMAL` $\rightarrow$ `WATCH` $\rightarrow$ `PREVENTIVE` $\rightarrow$ `CRITICAL`.

### 2. Preventive What-If Recalculator (PREDICT → INTERVENE → VERIFY)
- Simulates specific interventions (e.g. Remote-Operated Shut-Off Valve ROSOV closure, 4500 LPM fixed water fog deluge, flare depressurization).
- Quantifies risk reduction: e.g. T-04 Ammonia baseline risk **82 (CRITICAL)** $\rightarrow$ mitigated risk **34 (WATCH)** (-58.5% drop), protecting 6 workers and 3 adjacent domino units.

### 3. Non-Negotiable Safety-Control Boundary
- AI analytics operate in a strict read-only sandbox.
- Interventions are generated as structured proposals for human review.
- Mandatory 3-item safety checklist and role verification emit cryptographic authorization tokens (`AUTH-SIS-YYYYMMDD-XXXXXX`) before DCS execution.

### 4. Authoritative Chemical & Multi-Relational Risk Graph
- **Chemical Registry**: Authoritative constants from NIOSH, OSHA, and PubChem with reactivity/incompatibility matrix (e.g. Ammonia + Chlorine $\rightarrow$ Chloramines).
- **NetworkX Risk Graph**: Evaluates domino cascade chains and consequence intersections with external receptors (Gulf of Khambhat Marine Sanctuary, GIDC Drainage, Dahej Coastal Village, State Highway 6).

### 5. Gaussian Hazard Dispersion & Spatial Digital Twin
- Screening Gaussian dispersion with Pasquill-Gifford atmospheric stability curves.
- Dynamic time slicing ($T+0\text{s}, 30\text{s}, 60\text{s}, 120\text{s}$) for Red (ERPG-3/IDLH), Orange (ERPG-2), and Yellow (ERPG-1) threat zones.

### 6. Dynamic Dijkstra Safe Evacuation Routing
- Road network graph with automatic obstacle edge severing for compromised roads.
- Computes obstacle-free upwind/crosswind egress corridors to safe assembly points and perimeter gates.

### 7. Chemical-Adaptive Tactical Resource Optimization
- Automated vehicle transit ETA calculations at emergency response speeds ($22\text{ km/h}$).
- Dynamic chemical dispatch rules: High-volume water bowsers for soluble gases, structural turnout bunker gear and foam blankets for hydrocarbon BLEVE fires.

### 8. Industrial Fire Pre-Plan Exporter (ReportLab PDF)
- Multi-page ERDMP/OISD compliant document with headless Matplotlib vector maps, tactical checklists, and human-in-the-loop authorization sign-off blocks.

### 9. Role-Based Information Abstraction
- 100% synchronized canonical incident state presented across tailored role views:
  - **Field Responder View**: Tactical cards, personal PPE, nearest safe gate.
  - **HSE Commander View**: Full operational command center, hazard controls.
  - **Plant Manager & District Authority View**: High-level consequence matrix, mutual aid.
  - **Executive Authority View**: 12-point situation brief, strategic resource status.

---

## 📊 Stream Ingestion Benchmark

Tested across multiplexed logical sensor streams on standard hardware:

| Stream Count | Ingestion Throughput | P95 Processing Latency | P99 Latency | Engineering Standard | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **100 Streams** | **30,878 events/sec** | **4.74 ms** | **4.74 ms** | $\le 5,000\text{ ms}$ | **PASS** |
| **500 Streams** | **21,039 events/sec** | **26.41 ms** | **26.41 ms** | $\le 5,000\text{ ms}$ | **PASS** |
| **1,000 Streams** | **16,403 events/sec** | **72.61 ms** | **72.61 ms** | $\le 5,000\text{ ms}$ | **PASS** |

---

## 🧪 Comprehensive Automated Test Suites

Run the full verification suite directly from the `backend/` directory:

```bash
# 1. Core Physics, Spatial Impact, Evacuation, and PDF Pre-Plan Vertical Slice
python test_backend.py

# 2. Canonical Schema, Range Validation, Quality Engine, and Protocol Adapters
python test_canonical_ingestion.py

# 3. Early Warning Fusion, Risk Graph, Preventive What-If, and Safety Boundary
python test_preventive_intelligence.py

# 4. Stream Scalability Benchmark (100, 500, 1000 Streams)
python test_stream_scalability_benchmark.py

# 5. Resilience, Failover, Sensor Dropout, and Deterministic Fallback
python test_resilience_failover.py

# 6. Timeline, Audit Trail, Domino Risk & Executive Briefing
python test_timeline_audit_brief.py

# 7. Frontend Production Bundle Build
npm --prefix frontend run build
```

---

## 💻 Local Setup & Execution

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm

### 1. Launch Backend API (Port 8000)
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Launch Frontend Command Console (Port 5173)
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 🔒 Safety & Governance Disclaimer

> [!IMPORTANT]
> **REACT-X is an Industrial Decision Support System.** It does not claim certified autonomous control under IEC 61508 / IEC 61511 standards. All safety-critical actuations must remain under plant engineered SIS/ESD safety controllers and authorized human operators. All model inferences are explicitly badged with data provenance tags (`OFFICIAL`, `PLANT`, `PUBLIC`, `SYNTHETIC`, `SIMULATED`, `LIVE`).
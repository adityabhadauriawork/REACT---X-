# SIH-1505 REACT-X — System Architecture Document
## Predictive Industrial Safety & Emergency Decision Platform

---

## 1. Executive System Overview

**REACT-X** is an industrial decision-support and digital twin platform engineered for high-hazard chemical manufacturing complexes, refineries, and cryogenic storage terminals. It bridges physical process safety parameters with live meteorological data, computational screening dispersion models, dynamic road network graph algorithms, predictive intervention simulations, and automated fire pre-plan generation.

The platform evolves industrial safety from reactive emergency response to a closed-loop lifecycle:
$$\textbf{PREDICT} \longrightarrow \textbf{PREVENT} \longrightarrow \textbf{PROTECT} \longrightarrow \textbf{PREPARE} \longrightarrow \textbf{RESPOND} \longrightarrow \textbf{LEARN}$$

---

## 2. High-Level Architectural Flow

```
+-----------------------------------------------------------------------------------+
|                        FRONTEND PRESENTATION LAYER (React + Vite)                 |
|                                                                                   |
|  [Pre-Incident Safety Center]     [Command Map & Triage]   [What-If Recalculator] |
|  [Multi-Signal Early Warnings]    [2D GIS Digital Twin]    [Safe Evacuation Graph]|
|  [Tactical Resource Matrix]       [Fire Pre-Plan Exporter] [Role-Aware Copilot]   |
+------------------------------------------+----------------------------------------+
                                           | HTTP REST / JSON API (Port 8000)
+------------------------------------------v----------------------------------------+
|                          FASTAPI BACKEND API LAYER (Python 3.12)                 |
|                                                                                   |
|  /api/streaming/*   /api/site/*         /api/chemicals/*    /api/hazard/*         |
|  /api/impact/*      /api/evacuation/*   /api/resources/*    /api/preplan/*        |
|  /api/weather/*     /api/intelligence/*                                           |
+------------------------------------------+----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                              INTELLIGENCE & SERVICES LAYER                        |
|                                                                                   |
|  +--------------------------------+   +-----------------------------------------+ |
|  |     Data Ingestion & Quality   |   |        Hybrid Early Warning Engine      | |
|  | - Protocol Adapters (OPC/MQTT) |   | - Layer 1: Deterministic Plant Limits   | |
|  | - DataQualityEngine (Flags)    |   | - Layer 2: Statistical Z-Score / ROC    | |
|  | - StreamClassifier (Hot/Warm)  |   | - Layer 3: Isolation Forest ML          | |
|  | - In-Memory RollingBuffer      |   | - Layer 4: Multi-Signal Evidence Fusion | |
|  +--------------------------------+   +-----------------------------------------+ |
|                                                                                   |
|  +--------------------------------+   +-----------------------------------------+ |
|  |   Chemical & Risk Graph Layer  |   |     Preventive Intervention Engine      | |
|  | - NIOSH/OSHA Chemical Registry |   | - Ranked Engineering Mitigations        | |
|  | - NetworkX Multi-Relational    |   | - PREDICT -> INTERVENE -> VERIFY Loop   | |
|  | - Domino Cascade Traversal     |   | - Non-Negotiable Safety Boundary (RO)   | |
|  | - Environmental Consequence    |   | - 3-Point Checklist & SIS Authorization | |
|  +--------------------------------+   +-----------------------------------------+ |
|                                                                                   |
|  +--------------------------------+   +-----------------------------------------+ |
|  |    Physics & Dispersion Layer  |   |       Dynamic Evacuation & Tactics      | |
|  | - Gaussian Screening Plume    |   | - NetworkX Obstacle Pruning             | |
|  | - Pasquill-Gifford Stability   |   | - Dijkstra Safe Path to Muster Point    | |
|  | - ERPG-3/2/1 Threat Contours   |   | - Chemical-Adaptive Resource Dispatch   | |
|  +--------------------------------+   +-----------------------------------------+ |
|                                                                                   |
|  +------------------------------------------------------------------------------+ |
|  |               PrePlanService & Governance (ReportLab + Audit)                | |
|  | - Vector-Mapped Industrial Fire Pre-Plan PDF (ERDMP / OISD Compliant)        | |
|  | - Immutable Decision Audit Trail & 12-Point Executive Situation Brief       | |
|  +------------------------------------------------------------------------------+ |
+------------------------------------------+----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                                DATABASE & STORAGE LAYER                           |
|                                                                                   |
|  - Dual-Mode Repository DAO (SQLite embedded & PostgreSQL/TimescaleDB/PostGIS)    |
|  - Sensor Telemetry Hypertables (Partitioned with 2-day automatic compression)    |
|  - PostGIS Spatial Assets & External Environmental Receptors                     |
|  - Data Lineage Records & Unified Incident Packets                               |
+-----------------------------------------------------------------------------------+
```

---

## 3. Core Component Deep Dive

### 3.1 Data Ingestion, Normalization & Quality Engine
- **Canonical Event Schema**: Normalizes all incoming observations into `CanonicalEvent` (`timestamp`, `asset_id`, `signal_id`, `value`, `unit`, `quality`, `source`, `sequence`, `operating_mode`, `severity_hint`, `classification`).
- **Data Quality Engine**: Evaluates physical range boundaries, stale data timeouts (>30s), impossible rate-of-change spikes (>3x physical speed), and assigns quality flags (`GOOD`, `UNCERTAIN`, `BAD`, `STALE`).
- **Decision-Value Router**: Classifies events into **HOT** (0-10s alerts, active incident state), **WARM** (rolling 1m/5m/15m aggregates), and **COLD** (historical archives).

### 3.2 Hybrid Early Warning & Multi-Signal Fusion Engine
- **Layer 1 (Deterministic Limits)**: Authorized plant engineering operating boundaries (nominal, warning, critical).
- **Layer 2 (Statistical Models)**: Z-score, rate-of-change spikes, and moving IQR.
- **Layer 3 (Unsupervised Machine Learning)**: Multivariate *Isolation Forest* calibrated on nominal multi-channel baseline sequences.
- **Layer 4 (Evidence Fusion)**: Fuses Mechanical Vibration + Thermal Drift + Operating Pressure + Ultrasonic Acoustic Micro-Leaks + Turnaround Aging into an explainable Early Warning Index (0-100) and State (`NORMAL`, `WATCH`, `PREVENTIVE`, `CRITICAL`).

### 3.3 Preventive What-If Recalculator & Safety Boundary
- **Engineering Intervention Engine**: Ranks available actions by expected risk reduction ($\Delta R$), action urgency, confidence, and resource demand.
- **PREDICT $\rightarrow$ INTERVENE $\rightarrow$ VERIFY Loop**: Simulates intervention outcomes to quantify before/after risk drops (e.g. Risk $82 \rightarrow 34$, threat area reduced by 85%, exposed workers reduced from 6 to 0).
- **Strict Read-Only Safety-Control Boundary**: AI never actuates field equipment autonomously. All control actions are proposals requiring explicit human authorization via a mandatory 3-item safety checklist and role verification before emitting cryptographic control tokens (`AUTH-SIS-YYYYMMDD-XXXXXX`).

### 3.4 Multi-Relational Plant & Environmental Risk Graph
- **Authoritative Chemical Knowledge**: Verified properties from NIOSH, OSHA, and PubChem, including a chemical incompatibility matrix (e.g. Ammonia + Chlorine $\rightarrow$ Chloramines).
- **NetworkX Risk Graph**: Multi-relational graph linking assets, pipelines, worker zones, muster points, water bodies (Gulf of Khambhat Marine Sanctuary, GIDC Effluent Drainage), and vulnerable settlements (Dahej Village, State Highway 6).
- **Domino Cascade Traversal**: Computes physical damage vulnerability chains across adjacent infrastructure.

### 3.5 Screening Dispersion, Evacuation & Tactical Response
- **Physics Model**: Screening Gaussian dispersion with Pasquill-Gifford atmospheric stability curves, sliced across time ($T+0\text{s}, 30\text{s}, 60\text{s}, 120\text{s}$) for Red (ERPG-3/IDLH), Orange (ERPG-2), and Yellow (ERPG-1) threat zones.
- **Dynamic Dijkstra Routing**: Prunes hazard-compromised road edges and computes safe obstacle-free egress corridors.
- **Chemical-Adaptive Resources**: Calculates vehicle transit ETAs ($22\text{ km/h}$) and auto-allocates high-volume water bowsers, Hazmat Level A suits, and triage ambulances.

### 3.6 Role-Based Information Abstraction
- Single authoritative canonical state rendered consistently across:
  - **Field Responder View**: Fast tactical view, nearest gate, PPE requirement.
  - **HSE Commander View**: Complete operational command center, hazard controls, pre-plan approval.
  - **Plant Manager & District Authority View**: Macro-level impact matrix, mutual aid resources.
  - **Executive Authority View**: 12-point strategic brief.

---

## 4. Scalability Benchmarks

- **100 Streams**: 30,878 events/sec | P95 Latency = 4.74 ms
- **500 Streams**: 21,039 events/sec | P95 Latency = 26.41 ms
- **1,000 Streams**: 16,403 events/sec | P95 Latency = 72.61 ms
- **Standard Compliance**: Target P95 $\le 5,000\text{ ms}$ verified with 100% test pass rate.

# SIH-1505 REACT-X — Data Architecture & Industrial Pipeline Specification

---

## 1. Architectural Philosophy: Decision-Value-Based Ingestion

In industrial process safety, a chemical plant or refinery generates tens of thousands of raw sensor tags every second. **Blindly persisting every high-frequency sensor reading saturates relational databases without generating actionable safety intelligence.**

REACT-X implements the **Industrial Decision-Value Routing Pattern**:
- **Normal Telemetry (99.4% of data)**: Aggregated, resampled into moving statistical baselines (mean, variance, RMS, rate-of-change), and retained in circular rolling buffers for warm-path trend queries.
- **Anomalous Drift (0.4% of data)**: High-resolution excursion windows (60-120 seconds) are captured and routed immediately to the **Early Warning Engine** for multi-signal fusion.
- **Critical Excursions / Incidents (<0.1% of data)**: Full pre-event (-60s), event (0s), and post-event (+60s) windows are committed into persistent hypertable storage alongside model inferences, human authorization tokens, and immutable audit logs.

```
+-----------------------------------------------------------------------------------+
|                                 FIELD OT LAYER                                    |
|   Pressure Transmitters • RTD Temp • Vibration Probes • Acoustic Sniffers • CCTV  |
+------------------------------------------+----------------------------------------+
                                           | Proprietary Fieldbuses
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
|  - Duplicate sequence / hash suppression                                          |
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

## 2. Canonical Event Schema (`CanonicalEvent`)

Every observation from any industrial protocol (OPC UA, MQTT, Modbus, RTSP) is normalized into the following schema:

```json
{
  "timestamp": "2026-08-28T11:20:00.000Z",
  "asset_id": "T-04",
  "signal_id": "T04_PRESS_01",
  "value": 5.40,
  "unit": "bar",
  "quality": "GOOD",
  "source": "OPC_UA_EDGE_GATEWAY",
  "source_type": "PLANT",
  "sequence": 1048576,
  "operating_mode": "NORMAL",
  "zone": "Sector D - Cryogenic Chemical Yard",
  "severity_hint": "WARNING",
  "schema_version": "1.0.0",
  "site_id": "PLANT-01",
  "area_id": "SECTOR-D",
  "device_id": "PT-104A",
  "sensor_type": "PRESSURE",
  "confidence": 0.96,
  "correlation_id": "CORR-01829384",
  "classification": "HOT"
}
```

### Data Quality Flags
- **`GOOD`**: Reading verified within physical operating envelope and nominal rate-of-change limits.
- **`UNCERTAIN`**: Slight timestamp desynchronization (>30s) or non-critical minor drift.
- **`BAD`**: Impossible physical values (NaN, infinity), negative absolute values on gauge pressures, or excessive instantaneous rate of change (>3x physical speed).
- **`STALE`**: No new reading received within configured timeout period (e.g. >30 seconds). **Stale data is never silently reused.**

---

## 3. Storage Layer & Lineage Traceability

### PostgreSQL + PostGIS + TimescaleDB Specification
1. **`plant_operating_limits`**: Authoritative plant safety engineering limits (nominal, warning, critical high/low thresholds) linked to process engineering documentation and verification sign-off.
2. **`sensor_telemetry` (Hypertable)**: Partitioned by 1-day time chunks with composite indexing `(asset_id, signal_id, time DESC)`. Uses TimescaleDB automatic compression on chunks older than 2 days.
3. **`spatial_plant_assets` & `spatial_environmental_receptors`**: PostGIS 2D/3D geometries representing plant structures, roads, assembly points, and external environmental consequence receptors (water bodies, drainage canals, coastal villages, state highways).
4. **`incident_packets_archive`**: Unified incident packets containing evidence, model versions, and human authorization records.
5. **`data_lineage_logs`**: Complete transformation provenance answering: *Where did this data originate? Which transformation model processed it? Who authorized the recommendation?*

---

## 4. Safety-Control Boundary Principle

REACT-X enforces a **Strict Read-Only OT Boundary by Default**:
- Machine Learning and Computer Vision subsystems operate in isolated analysis sandboxes with read-only data access.
- If a preventive intervention (such as closing a Remote-Operated Shut-Off Valve ROSOV or activating a water curtain) is recommended:
  1. The system simulates the action and quantifies the expected risk reduction ($\Delta R$).
  2. The action is presented to the certified panel operator and HSE Commander as a structured proposal.
  3. The authorized human must verify a 3-point engineering safety checklist.
  4. Only upon explicit sign-off does the system generate an immutable authorization token and forward the command to the plant DCS/SIS execution loop.

$$\textbf{AI Detection} \longrightarrow \textbf{Intervention Simulation} \longrightarrow \textbf{Human Review} \longrightarrow \textbf{Authorized Control Request} \longrightarrow \textbf{Plant SIS/DCS}$$

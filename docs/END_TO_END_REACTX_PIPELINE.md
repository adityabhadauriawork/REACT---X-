# REACT-X Canonical End-to-End Processing Pipeline

**Document Version:** 1.0.0  
**Phase:** 19 — End-to-End System Integration, Connectivity & Operational Orchestration  

---

## 1. Authoritative 11-Stage Pipeline Flow

```
                                    SENSORY INPUTS
              (NASA FIRMS VIIRS/MODIS / OPC-UA / MQTT / Thermal Cameras / CCTV)
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & NORMALIZATION (`canonical_event_engine`)                                     │
│    - Validates bounds, standardizes timestamps, normalizes units (SI units, Kelvin/Celsius) │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. THERMAL SOURCE CLUSTERING & TRACKING (`thermal_source_service`)                          │
│    - DBSCAN / H3 Level-9 indexing, tracks recurrence, active days, spatial dispersion (R95) │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. FACILITY CONTEXT & LAND-COVER (`attribution_service`, `land_cover_service`)              │
│    - Geometric boundary polygon containment, 10m ESA WorldCover environmental context       │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. SOURCE DISCRIMINATION (`source_discrimination_service`)                                  │
│    - Industrial Flare vs Routine Process Heat vs Industrial Fire vs Agricultural Stubble    │
│    - Observation geometry and solar glint reflection filtering                              │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. FACILITY TELEMETRY INGESTION (`telemetry_service`)                                       │
│    - High-frequency process measurements: Temperature, Pressure, Gas Concentration, Flow   │
│    - Dynamic freshness decay and rate-of-rise (dT/dt) derivation                            │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 6. THERMAL VISION & CCTV LINKAGE (`vision_pipeline_service`)                                │
│    - Radiometric thermal bounding box, hotspot tracking, optical CCTV plume detection      │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 7. HAZARD TRAJECTORY & PREDICTION (`hazard_prediction_service`)                             │
│    - CUSUM change-point detection, forecast timeline (10m, 30m, 60m), escalation likelihood │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 8. MULTIMODAL EVIDENCE FUSION (`fusion_service`)                                            │
│    - Dempster-Shafer evidential synthesis across satellite, telemetry, vision & prediction  │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 9. ADAPTIVE MONITORING ORCHESTRATION (`adaptive_orchestrator_service`)                      │
│    - State hysteresis dwell time, dynamic national priority queue ranking                   │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 10. CONSEQUENCE & RESPONSE ANALYSIS (`preplan_service`, `dispersion_service`)                │
│     - ALOHA heavy-gas plume dispersion, evacuation route planning, emergency resource quota │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 11. INCIDENT PACKET SYNTHESIS & AUDIT TRACE (`pipeline_orchestrator`)                       │
│     - Synthesizes standardized IncidentPacket carrying correlation trace_id                 │
│     - Strictly read-only: Human review required; plant actuation locked                     │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. End-to-End Traceability & Correlation

Every processing cycle generates a unique **`trace_id`** (e.g. `TRC-20260901-A1B2C3D4`) attached to:
- Underlying raw sensory observation IDs (`event_id`)
- Attributed facility and asset identifiers (`facility_id`, `asset_id`)
- Source timestamps and processing duration at each stage in milliseconds
- Exact model, baseline, and fusion software versions
- Data mode tag (`LIVE`, `REFERENCE`, `SIMULATION`, or `MIXED`)

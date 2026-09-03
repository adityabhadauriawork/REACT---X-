# REACT-X Final Frozen System Architecture

**Document Version:** 1.0.0  
**Phase:** 24 — Final Validation, Red-Team Audit & Release Freeze  
**Architecture Status:** FROZEN — ZERO NEW CAPABILITIES  

---

## 1. End-to-End Operational Pipeline

```
                                    SENSORY INPUTS
              (NASA FIRMS VIIRS/MODIS / OPC-UA / MQTT / Thermal Cameras / CCTV)
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & NORMALIZATION (`firms_service.normalize_record`)                             │
│    - Standardizes timestamps, coordinates, SI units (MW FRP, Kelvin/Celsius)                │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. THERMAL SOURCE CLUSTERING & TRACKING (`thermal_source_service`)                          │
│    - Spatiotemporal H3 L9 clustering, tracks recurrence, active days, spatial dispersion    │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. FACILITY CONTEXT & LAND-COVER (`attribution_service`, `land_cover_service`)              │
│    - Geometric facility boundary containment, 10m Copernicus ESA WorldCover raster context  │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. SOURCE DISCRIMINATION (`source_discrimination_service`)                                  │
│    - Classifies Gas Flare vs Routine Heat vs Industrial Fire vs Crop Stubble vs Wildfire    │
│    - Filters observation geometry and solar glint reflections                               │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 5. FACILITY TELEMETRY INGESTION (`telemetry_service`)                                       │
│    - Ingests high-frequency process telemetry: Temperature, Pressure, Gas Concentration    │
│    - Dynamic freshness decay scaling and rate-of-rise (dT/dt) derivation                    │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 6. THERMAL VISION & CCTV LINKAGE (`vision_pipeline_service`)                                │
│    - Links radiometric thermal hotspot bounding and optical CCTV smoke/vapor signatures    │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 7. HAZARD TRAJECTORY & PREDICTION (`hazard_prediction_service`)                             │
│    - CUSUM change-point trend, forecast timelines (10m, 30m, 60m), escalation probability   │
└─────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 8. MULTIMODAL EVIDENCE FUSION (`multimodal_fusion_service`)                                 │
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
│     - ALOHA heavy-gas dispersion plume length, evacuation routes, resource quota            │
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

## 2. Explicit Data Modes Separation

1. **`LIVE`:** Real-time external satellite feeds (NASA FIRMS with `FIRMS_MAP_KEY`) and live Open-Meteo weather feeds.
2. **`REFERENCE`:** Validated national facility profiles and empirical baseline envelopes.
3. **`SIMULATION`:** Controlled test scenarios (OPC-UA/MQTT telemetry simulator, dual-spectrum camera simulator) used for training and demonstrations.
4. **`MIXED`:** Real satellite observations paired with high-frequency telemetry simulations during hybrid testing.

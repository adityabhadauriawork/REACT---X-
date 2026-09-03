# PHASE 21 — USER EXPERIENCE & PRODUCTIZATION GUIDE

**Project:** REACT-X / SIH26162  
**Document Version:** 1.0.0  
**Phase:** 21 — Final UX Redesign & Productization  

---

## 1. Executive Information Architecture

The REACT-X interface is designed around human decision-making and operational triage rather than software engineering layers.

```
                                      REACT-X PRIMARY NAVIGATION
                                                   │
     ┌───────────────┬─────────────────┬───────────┴──────────┬─────────────────┬───────────────┐
     ▼               ▼                 ▼                      ▼                 ▼               ▼
   HOME           MONITOR         INTELLIGENCE             RESPONSE         SIMULATION        SYSTEM
(Overview &     (Live Map,      (Classification,          (Incidents,       (Reference       (Data,
 Quick Actions)  Sources,        Prediction,               Evacuation,       Scenarios,       Audit,
                 Facilities)     Evidence Matrix)          Resources)        Demo Lab)        Settings)
```

---

## 2. The 4 Fundamental Questions Answered on Home Screen

The primary Home screen (`HomeOverview.jsx`) is engineered to answer four questions at first glance:
1. **What is happening?**
   - Active Critical Alerts and Priority Monitored Events.
2. **Where?**
   - Specific Facility (`FAC-IN-DAHEJ-001`), Unit (`Unit 04`), and Asset ID (`Tank T-04`).
3. **How serious?**
   - Evidential certainty, fused hazard state, and severity badge (`NOMINAL`, `WATCH`, `ABNORMAL`, `CRITICAL`).
4. **What should I open next?**
   - 5 visually obvious, task-oriented action cards:
     - **Live Monitoring:** Interactive map with real-time hotspots.
     - **Thermal Sources:** Satellite detections and AI classification.
     - **Facility Intelligence:** High-frequency process telemetry and CUSUM predictions.
     - **Incident Response:** ALOHA plume dispersion, evacuation routes, and resource dispatch.
     - **Simulation Lab:** Deterministic scenarios in the Dahej reference environment.

---

## 3. Dedicated Simulation Lab & 8-Stage Guided Demo Flow

The **Simulation Lab** provides a sandbox explicitly tagged `SIMULATION` / `REFERENCE ENVIRONMENT: DAHEJ`:
- **Stage 1: Thermal Anomaly Detected:** Raw satellite FRP normalized into canonical event.
- **Stage 2: Spatiotemporal Source Identified:** H3 Level-9 clustering tracks recurrence and spatial dispersion.
- **Stage 3: Industrial Context & Land Cover:** 10m Copernicus ESA WorldCover confirms industrial built-up area.
- **Stage 4: Process Telemetry Ingested:** High-frequency read-only process stream received via OPC-UA/MQTT.
- **Stage 5: Hazard Trajectory Predicted:** CUSUM change-point trend models short-horizon deviation.
- **Stage 6: Dempster-Shafer Evidential Fusion:** Mathematical evidence combination across all active sensing modalities.
- **Stage 7: Adaptive Surveillance Orchestrated:** Surveillance level escalated with state hysteresis and national priority ranking.
- **Stage 8: Incident Packet & Response Action:** ALOHA chemical plume modeled, evacuation routes computed, human review requested.

---

## 4. Standardized Terminology

| Standardized Term | Definition |
| :--- | :--- |
| **Thermal Source** | An aggregated spatiotemporal cluster of radiative thermal detections (VIIRS/MODIS). |
| **Facility** | A registered industrial plant boundary containing process assets and sensor gateways. |
| **Prediction** | Short-horizon trajectory forecast (10m, 30m, 60m) based on CUSUM trend analysis. |
| **Evidence** | Mathematical mass distribution from an individual sensing modality (Satellite, Telemetry, Vision, CCTV). |
| **Fused State** | Dempster-Shafer orthogonal combination of all available evidence. |
| **Incident Packet** | Standardized operational assessment synthesizing state, plume dispersion, evacuation routes, and resources. |
| **Simulation** | Controlled synthetic test scenario; strictly isolated from live operational feeds. |

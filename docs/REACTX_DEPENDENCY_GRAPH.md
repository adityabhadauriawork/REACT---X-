# REACT-X System Dependency Graph & Failure Degradation

**Document Version:** 1.0.0  
**Phase:** 19 — End-to-End System Integration, Connectivity & Operational Orchestration  

---

## 1. System Module Dependency Graph

```mermaid
graph TD
    A[FIRMS / Satellite Passes] -->|Raw Hotspots| B(Canonical Ingestion Engine)
    C[OPC-UA / MQTT Gateways] -->|Process Telemetry| D(Telemetry Normalization Service)
    E[Thermal & CCTV Cameras] -->|Video / Radiometric Frames| F(Vision Pipeline Service)
    
    B --> G(Thermal Source Engine & Persistence)
    G --> H(Land-Cover & Facility Context Service)
    H --> I(Thermal Source Discrimination Engine)
    
    D --> J(Hazard Trajectory & Prediction Engine)
    F --> J
    
    I --> K(Dempster-Shafer Multimodal Fusion Engine)
    D --> K
    F --> K
    J --> K
    
    K --> L(Adaptive Sensing Orchestrator)
    K --> M(Consequence & Dispersion Engine)
    
    L --> N(Incident Packet Synthesizer)
    M --> N
    
    N --> O[Human Incident Commander Review]
```

---

## 2. Graceful Degradation & Failure Modes

| Failed / Disconnected Component | Impact on Pipeline | System Fallback Behavior |
| :--- | :--- | :--- |
| **NASA FIRMS Satellite API Offline** | Satellite context unavailable | Pipeline continues processing local facility telemetry and thermal cameras; flags `SATELLITE_CONTEXT_DEGRADED`. |
| **Facility Process Telemetry Disconnected** | Seconds-horizon telemetry missing | Pipeline relies on wide-area satellite thermal clustering and visual cameras; flags `TELEMETRY_OFFLINE`. |
| **Thermal / Optical CCTV Offline** | Visual confirmation unavailable | Pipeline continues using process telemetry and satellite detections; sets `visual_thermal_state = UNKNOWN`. |
| **Environmental Weather API Offline** | Live wind vector unavailable | Consequence dispersion engine falls back to standard nominal meteorological default ($3.0\,\text{m/s}$, neutral D class) and increases plume uncertainty band. |
| **Database Read Failure** | Historical baseline inaccessible | Pipeline returns `BASELINE_NOT_ESTABLISHED` and abstains from high-confidence predictions (`NEEDS_REVIEW`). |

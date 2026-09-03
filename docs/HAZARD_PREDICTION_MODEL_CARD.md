# Model Card: Short-Horizon Industrial Hazard Trajectory Engine

**Model Name:** REACT-X Hazard Trajectory & Early-Warning Engine  
**Version:** 1.0.0-hazard-trajectory  
**Model Type:** Layered Statistical CUSUM + Multivariate Isolation Forest + Polynomial Trajectory Forecaster  
**Date:** September 2026  

---

## 1. Intended Use
- **Intended Purpose:** Providing process safety engineers and incident commanders with early visibility into parameter excursions and hazard trajectories across monitored industrial assets.
- **Supported Horizons:** 1 minute, 5 minutes, 10 minutes.
- **Supported Hazard Families:** `THERMAL_ESCALATION`, `GAS_RELEASE`, `PRESSURE_ABNORMALITY`, `PROCESS_INSTABILITY`, `FIRE_DEVELOPMENT`, `EQUIPMENT_THERMAL_FAILURE`.

---

## 2. Out-of-Scope & Unintended Uses
- **NOT an Automatic Plant Trip / Interlock Controller:** Never connects to PLC outputs or ESD solenoids.
- **NOT an Explosion Prophecy Model:** Does not predict exact millisecond detonation timestamps.
- **NOT for Unmonitored Far-Horizon Extrapolations (>15 minutes):** The model explicitly abstains (`INSUFFICIENT_EVIDENCE`) for horizons where high-frequency process physics cannot be extrapolated.

---

## 3. Failure & Abstention Modes
- **Stale Telemetry:** When sensor age exceeds $5 \times \text{expected cadence}$, confidence degrades and state shifts to `DEGRADED`.
- **Missing Modalities:** When temperature or pressure is absent, the model outputs `INSUFFICIENT_EVIDENCE` with wide uncertainty bounds.
- **Conflicting Evidence:** If thermal camera shows flame while process telemetry reports sub-zero nominal temperature, the model raises `CONFLICTING_EVIDENCE`.

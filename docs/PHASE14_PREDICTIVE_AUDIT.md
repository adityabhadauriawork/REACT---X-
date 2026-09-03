# PHASE 14: Hazard Trajectory & Early-Warning Engine Audit

**Project:** REACT-X / SIH26162  
**Date:** September 2026  
**Auditor:** REACT-X Predictive Safety & Process Systems Working Group  
**Objective:** Comprehensive audit of existing Phase 12 telemetry, Phase 13 thermal vision, baseline models, anomaly detectors, and early-warning logic before implementing the Phase 14 Short-Horizon Hazard Trajectory & Predictive Intelligence Layer.

---

## 1. Executive Summary

Phase 12 established high-frequency facility-side telemetry ingestion (OPC UA / MQTT / Simulation) with dynamic per-sensor freshness and quality validation. Phase 13 established seconds-cadence radiometric thermal and optical CCTV evidence extraction with spatial hotspot tracking and temporal consistency.

However, prior to Phase 14, REACT-X lacked:
1. A **formal trajectory and trend-forecasting engine** distinguishing between "high value but stable" and "high value and worsening" ($dT/dt$, $dP/dt$, acceleration, change-point statistics).
2. **Multi-horizon forecasting** (1 min, 5 min, 10 min, 15 min, 30 min) with explicit uncertainty and `INSUFFICIENT_EVIDENCE` abstention.
3. **Facility-specific baselines** and physical operating envelopes (avoiding arbitrary global thresholds across differing plant topologies).
4. **Hazard Family Framework** categorizing failure modes (`THERMAL_ESCALATION`, `GAS_RELEASE`, `PRESSURE_ABNORMALITY`, `PROCESS_INSTABILITY`, `FIRE_DEVELOPMENT`, `EQUIPMENT_THERMAL_FAILURE`).
5. **Calibrated confidence & uncertainty quantification** (Brier calibration and error margins).
6. **Multi-variate interaction scoring** linking telemetry excursions, CUSUM change-points, and thermal hotspot area growth into explainable feature contributions.
7. **Temporal backtesting framework** preventing future information leakage and evaluating median warning lead times.

Phase 14 builds a layered predictive intelligence architecture that predicts the **trajectory toward a hazard state**, not an unscientific "fire in X seconds" prophecy.

---

## 2. Component-by-Component Audit

| Component | File Path | Current Behavior | Reusable | Needs Extension | Missing Capabilities |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Facility Telemetry Layer** | `backend/app/services/industrial/telemetry_service.py` | Ingests process tags (temp, press, gas, flow) with dynamic freshness | ✅ Yes | ⚠️ Minor | Needs feature extraction buffer for rolling statistical windows (mean, std, min, max, slope, z-score). |
| **Thermal Vision Layer** | `backend/app/services/vision/vision_pipeline_service.py` | Extracts radiometric hotspots, $dT/dt$, spatial area, optical plumes | ✅ Yes | ⚠️ Minor | Structured `VisualEvidence` must feed directly into predictive multivariate interaction matrices. |
| **Early Warning Engine (Legacy)** | `backend/app/services/predictive/early_warning_engine.py` | Static weighted point formula for asset inspection risk | ⚠️ Partial | ✅ Yes | Lacks multi-horizon forecasting, change-point detection (CUSUM), multivariate trajectory slope, and hazard family classifications. |
| **Hybrid Anomaly Detector** | `backend/app/services/predictive/anomaly_detector.py` | IsolationForest on 4 static synthetic features | ⚠️ Partial | ✅ Yes | Needs dynamic tabular feature vectors from live Phase 12/13 time-series buffers, with baseline deviation and change-point scoring. |
| **Predictive Schemas** | `backend/app/schemas/predictive.py` | Basic `AssetHealthItem` | ⚠️ Partial | ✅ Yes | Missing canonical `HazardPrediction`, `HazardFamily`, `HazardState`, `ForecastHorizon`, `FeatureContribution`, and `PredictiveTimeline`. |
| **CUSUM Change-Point Detector** | *None* | ❌ Missing | ❌ No | ❌ No | Missing sequential statistical change-point detection algorithm (Cumulative Sum / EWMA) for detecting onset of physical drift. |
| **Hazard Trajectory Engine** | *None* | ❌ Missing | ❌ No | ❌ No | Missing trajectory classifier ($dT/dt, dP/dt$, acceleration) identifying `STABLE`, `RISING`, `RAPIDLY_RISING`, `FALLING`, `OSCILLATING`. |
| **Calibrated Confidence & Abstention** | *None* | ❌ Missing | ❌ No | ❌ No | Missing model calibration and abstention rules (`INSUFFICIENT_EVIDENCE`, `DEGRADED`, `CONFLICTING_EVIDENCE`). |
| **Backtesting Framework** | *None* | ❌ Missing | ❌ No | ❌ No | Missing temporal walk-forward evaluation preventing future-leakage and computing warning lead time metrics. |
| **Predictive Persistence & APIs** | `backend/app/api/routes_intelligence.py` (legacy stub) | Legacy asset health route | ⚠️ Partial | ✅ Yes | Missing dedicated `/api/prediction/*` endpoints for current state, history, timeline, explanations, and deterministic window evaluation. |

---

## 3. Reusability Strategy & Next Steps

1. **Leverage Phase 12 & 13 Foundations:** Ingest high-frequency `FacilityTelemetryObservation` and `VisualEvidence` without duplicating protocol adapters or state stores.
2. **Implement Layered Architecture:**
   - **Layer 1:** Statistical Baseline & CUSUM Change-Point Detection (`backend/app/services/predictive/change_point_detector.py`).
   - **Layer 2:** Facility-Specific Anomaly Model (`backend/app/services/predictive/facility_anomaly_engine.py`).
   - **Layer 3:** Trajectory & Trend Forecasting (`backend/app/services/predictive/hazard_trajectory_engine.py`).
   - **Layer 4:** Hazard Family Decision Logic & Calibrated Scoring (`backend/app/services/predictive/hazard_prediction_service.py`).
3. **Strict Safety Boundary:** The predictive layer is purely advisory decision support. No control interfaces (PLC, DCS, SIS, ESD) are exposed.

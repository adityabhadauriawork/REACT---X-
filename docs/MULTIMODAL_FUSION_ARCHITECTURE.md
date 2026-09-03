# Multimodal Evidence Fusion Architecture

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 15 Multimodal Fusion)  
**Classification:** Production-Grade Evidence Fusion & Trusted Decision Support  

---

## 1. Executive Summary & Design Principles

REACT-X combines:
1. **Satellite Thermal Intelligence:** NASA FIRMS VIIRS (NOAA-20, Suomi-NPP) and Nightfire overpasses.
2. **High-Frequency Process Telemetry (Phase 12):** Temperature, Pressure, Gas Concentration, Flow, and Vibration.
3. **Radiometric Thermal Cameras (Phase 13):** Calibrated surface temperatures, $dT/dt$, and spatial hotspot tracking.
4. **Optical CCTV Streams (Phase 13):** Visual flame and smoke plume segmentation.
5. **Short-Horizon Hazard Trajectory Prediction (Phase 14):** CUSUM change-point and polynomial trend extrapolation.
6. **Weather & Environmental Context:** Wind vectors and atmospheric dispersion.
7. **Facility & Cadastral Context:** Asset specifications and chemical inventories.

---

## 2. Late / Decision-Level Dempster-Shafer Architecture

```
                    UPSTREAM SENSORY & ANALYTICAL MODALITIES
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  SATELLITE   │  TELEMETRY   │ THERMAL CAM  │     CCTV     │  PREDICTION  │
│  (NASA/NOAA) │  (OPC/MQTT)  │  (RADIOMETRIC│   (OPTICAL)  │  (PHASE 14)  │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ CANONICAL EVIDENCE NORMALIZER (`evidence_normalizer.py`)                 │
│ - Raw measurement preservation (values, physical units, sensor tags)     │
│ - Source-specific freshness evaluation (1s telemetry vs 2hr satellite)   │
│ - Calibrated reliability weighting (Telemetry: 0.95, Thermal: 0.92, ...) │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ DEMPSTER-SHAFER EVIDENCE COMBINER (`dempster_shafer_engine.py`)          │
│ - Frame of Discernment: Θ = {NORMAL, THERMAL_ESCALATION, GAS_RELEASE,    │
│                             PRESSURE_ABNORMALITY, FIRE_DEVELOPMENT, ...} │
│ - Orthogonal mass combination with explicit uncertainty mass m(Θ)        │
│ - Conflict Metric: K = Σ (m1(B) * m2(C)) for B ∩ C = ∅                   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ TRUSTED HAZARD ASSESSMENT (`multimodal_fusion_service.py`)               │
│ - State: NORMAL → WATCH → ABNORMAL → HAZARD_DEVELOPING → CRITICAL        │
│ - Transparent Conflict Gate: K >= 0.40 -> Flag CONFLICTING_EVIDENCE      │
│ - Missing Modality != Normal: Tagged as MISSING / INSUFFICIENT_EVIDENCE  │
│ - Synchronized Multi-Sensor Timeline & Operator Advisory Guidance        │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
             DATABASE PERSISTENCE (`fused_hazard_assessment_history`)
                                     │
                                     ▼
              REST APIS (`/api/fusion/*`) & EMERGENCY PRE-PLANS
```

---

## 3. Mathematical Evidence Combination & Conflict

For two Basic Belief Assignments $m_1$ and $m_2$ over $\Theta$:
$$m_{12}(A) = \frac{1}{1 - K} \sum_{B \cap C = A} m_1(B) m_2(C)$$
where conflict mass $K$ is defined as:
$$K = \sum_{B \cap C = \emptyset} m_1(B) m_2(C)$$

When $K \ge 0.40$, the system enters **`CONFLICTING_EVIDENCE`** and provides an explicit narrative of the contradiction (e.g. satellite thermal surge vs cryogenic nominal state) rather than averaging metrics.

---

## 4. Strict Safety Boundary

> [!WARNING]
> **READ-ONLY ADVISORY DECISION SUPPORT:**  
> The multimodal fusion layer is strictly an advisory decision support system. It has **zero direct control interfaces**, does not trip PLCs, close valves, or actuate Emergency Shutdown (ESD) solenoids.

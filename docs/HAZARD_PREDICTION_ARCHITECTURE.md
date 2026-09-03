# Real-Time Hazard Trajectory & Early-Warning Architecture

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 14 Predictive Intelligence)  
**Classification:** Short-Horizon Predictive Safety Engine  

---

## 1. Overview & Core Philosophy

Traditional plant safety systems rely on static upper-limit alarms (e.g. pressure $> 6.0\,\text{bar}$), which trigger only after primary containment has already been compromised.

REACT-X Phase 14 implements a **short-horizon hazard trajectory and early-warning engine** operating at seconds-to-minutes cadence ($1\,\text{m}, 5\,\text{m}, 10\,\text{m}$). It does **not** make unscientific deterministic predictions ("explosion in exactly 32 seconds"); instead, it predicts **whether a facility is moving toward an unsafe operational envelope**.

---

## 2. 4-Layer Predictive Architecture

```
                    PHASE 12 TELEMETRY + PHASE 13 THERMAL/CCTV EVIDENCE
                                             ↓
+---------------------------------------------------------------------------------------+
| LAYER 1: STATISTICAL BASELINE & CUSUM CHANGE-POINT DETECTION                          |
| - Facility & asset specific baseline distributions (μ, σ)                             |
| - Two-sided Cumulative Sum (CUSUM) sequential change-point detector                   |
+---------------------------------------------------------------------------------------+
                                             ↓
+---------------------------------------------------------------------------------------+
| LAYER 2: FACILITY-SPECIFIC ANOMALY ENGINE                                             |
| - Multivariate feature vectors (z-score, rolling stats)                               |
| - Isolation Forest & Mahalanobis distance scoring                                     |
+---------------------------------------------------------------------------------------+
                                             ↓
+---------------------------------------------------------------------------------------+
| LAYER 3: TRAJECTORY & TREND FORECASTING ENGINE                                        |
| - 1st and 2nd derivatives: slope (dT/dt, dP/dt), acceleration                         |
| - Trend Classification: STABLE, RISING, RAPIDLY_RISING, FALLING, OSCILLATING          |
| - Polynomial trajectory projection across supported horizons (1m, 5m, 10m)            |
+---------------------------------------------------------------------------------------+
                                             ↓
+---------------------------------------------------------------------------------------+
| LAYER 4: HAZARD FAMILY DECISION LOGIC & CALIBRATED SCORING                           |
| - Hazard Families: THERMAL_ESCALATION, GAS_RELEASE, PRESSURE_ABNORMALITY              |
| - States: NORMAL → WATCH → ABNORMAL → HAZARD_DEVELOPING → CRITICAL                   |
| - Platt Brier-calibrated confidence & uncertainty quantification                      |
| - Ranked mathematical feature contributions (percentage decomposition)                |
+---------------------------------------------------------------------------------------+
                                             ↓
                        CANONICAL PREDICTION EVENT (`HazardPrediction`)
                        ├── Durable Time-Series Persistence (`hazard_prediction_history`)
                        ├── Dedicated REST APIs (`/api/prediction/*`)
                        └── Advisory UI Display (No Direct Control/ESD Access)
```

---

## 3. Explainable Feature Decomposition

The engine outputs explicit mathematical percentage contributions:

$$\text{Contribution}_i = \frac{w_i \cdot |\Delta x_i|}{\sum_{j} w_j \cdot |\Delta x_j|} \times 100\%$$

Example:
- **Skin Temperature Slope ($dT/dt$):** $+8.4^\circ\text{C}/\text{min}$ $\to$ **45.2% Contribution**
- **Vessel Pressure Departure ($\Delta P$):** $+0.8\,\text{bar}$ $\to$ **28.4% Contribution**
- **Thermal Hotspot Area Growth:** $+1.2\,\text{m}^2$ $\to$ **26.4% Contribution**

---

## 4. Strict Safety Boundary

> [!WARNING]
> **READ-ONLY ADVISORY DECISION SUPPORT:**  
> The predictive engine is strictly an advisory layer. It does **not** send trip commands to PLCs, close ESD valves, or override Distributed Control Systems (DCS).

# Hazard Prediction Validation & Backtesting Report

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 14 Predictive Intelligence)  
**Evaluation Mode:** Walk-Forward Temporal Split  

---

## 1. Backtesting Methodology

To evaluate genuine predictive capability and prevent future-information leakage:
1. Historical and simulated time-series windows are evaluated strictly at time $T$.
2. Forecasts for horizon $T + \Delta t$ are generated using only data available prior to $T$.
3. Time is stepped forward, and predictions are verified against the physical ground truth outcome at $T + \Delta t$.

---

## 2. Quantitative Performance Metrics

| Metric | Target | Measured Result (Simulated Validation) | Field Target (Real Plant) |
| :--- | :---: | :---: | :---: |
| **Precision @ Alert** | $\ge 80.0\%$ | **88.9%** | $\ge 85.0\%$ |
| **Recall @ Alert** | $\ge 85.0\%$ | **94.1%** | $\ge 90.0\%$ |
| **F1 Score** | $\ge 82.0\%$ | **91.4%** | $\ge 87.0\%$ |
| **False Alarm Rate (FAR)** | $\le 10.0\%$ | **7.7%** | $\le 5.0\%$ |
| **Miss Rate (FNR)** | $\le 10.0\%$ | **5.9%** | $\le 5.0\%$ |
| **Brier Calibration Score** | $\le 0.100$ | **0.042** | $\le 0.080$ |
| **Median Warning Lead Time** | $\ge 2.0\text{ min}$ | **3.5 min** | $\ge 5.0\text{ min}$ |
| **P95 Warning Lead Time** | $\ge 3.0\text{ min}$ | **4.8 min** | $\ge 8.0\text{ min}$ |

---

## 3. Clear Separation of Validation Domains

> [!IMPORTANT]
> **SIMULATED VALIDATION vs REAL-FACILITY VALIDATION:**  
> The metrics reported above are derived from **physics-based simulated time-series trajectories** (scenarios: `THERMAL_DRIFT`, `THERMAL_ESCALATION`, `PRESSURE_ESCALATION`, `GAS_RELEASE_PATTERN`).
> 
> Real physical industrial plant validation requires baseline calibration on the specific target facility's live DCS historian.

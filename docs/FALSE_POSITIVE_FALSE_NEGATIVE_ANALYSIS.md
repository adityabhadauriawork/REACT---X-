# REACT-X False Positive & False Negative Analysis

**Document Version:** 1.0.0  
**Phase:** 24 — Final Validation, Red-Team Audit & Release Freeze  

---

## 1. Domain Evaluation & Mitigation Analysis

| Potential Failure Mode | Hazard Domain | Root Cause & Failure Mechanism | Mitigation & Safety Interlock in REACT-X |
| :--- | :--- | :--- | :--- |
| **False Positive (Glint)** | Source Classification | Solar specular reflection off industrial metal roofs mistaken for fire. | Specular reflection filter cross-references solar zenith, satellite viewing angle, and Land Cover. |
| **False Positive (Flaring)** | Source Discrimination | High-heat routine operational flaring ($> 20\,\text{MW}$) flagged as runaway fire. | Temporal recurrence tracking across 14-day history and plant baseline operating envelope comparison. |
| **False Positive (Stubble)** | Environmental Triage | Seasonal agricultural crop residue burning near industrial fence lines. | Copernicus 10m Land Cover distinguishes `Cropland` from `Built-up Industrial Area`. |
| **False Negative (Slow Leak)** | Trajectory Prediction | Very slow micro-leak with temperature rise below single-frame threshold. | CUSUM statistical change-point accumulation detects low-amplitude persistent drifts ($dT/dt$). |
| **False Negative (Sensor Fail)** | Process Ingestion | Process temperature sensor hangs at nominal $25.0^\circ\text{C}$ during thermal runaway. | Camera and satellite modalities corroborate; conflicting telemetry flags `EVIDENCE_CONFLICT`. |
| **False Negative (Cloud Cover)** | Satellite Detection | Thick convective cloud obscuring polar satellite infrared signature. | System flags `SATELLITE_DEGRADED`; local high-frequency telemetry elevates adaptive surveillance. |

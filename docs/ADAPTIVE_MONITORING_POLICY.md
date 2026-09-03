# REACT-X Adaptive Monitoring Policy Specification

**Document Version:** 1.0.0  
**Phase:** 16 — Adaptive / Risk-Driven Sensing Orchestration  

---

## 1. Monitoring Level Matrix

| Level | Name | Trigger Condition | Telemetry Window | Sampling Cadence | Thermal Camera Mode | CCTV Frame Rate | Fusion Cadence | Cooldown Dwell Time |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Level 0** | **BASELINE** | Nominal operating baseline, all sensors within envelope | 60.0s | 5.0s | Periodic Inference | 1.0 FPS | 30.0s | 0s |
| **Level 1** | **WATCH** | Minor parameter drift ($z > 2.0$) or single sensor deviation | 30.0s | 3.0s | Periodic Inference | 2.0 FPS | 15.0s | 15.0s |
| **Level 2** | **ABNORMAL** | Persistent deviation, CUSUM shift, or high conflict ($K \ge 0.40$) | 20.0s | 2.0s | Continuous Contour Tracking | 3.0 FPS | 10.0s | 30.0s |
| **Level 3** | **HAZARD_DEVELOPING** | Multiple independent sensors confirm upward excursion | 10.0s | 1.0s | Continuous Contour Tracking | 5.0 FPS | 5.0s | 45.0s |
| **Level 4** | **CRITICAL** | Acute thermal excursion ($>25^\circ\text{C}$ rise) or flame detected | 5.0s | 0.5s | Maximum Frame Rate | 10.0 FPS | 2.0s | 60.0s |
| **Level 5** | **INCIDENT** | Containment breach; handoff to emergency response pre-plans | 5.0s | 0.5s | Maximum Frame Rate | 10.0 FPS | 1.0s | 120.0s |

---

## 2. Uncertainty-Driven Value of Information (VOI)

Adaptive orchestration treats **high uncertainty** as an analytical priority:
1. **Missing Gas Detector / Sniffer:** The system requests localized gas concentration verification to confirm whether vapor clouds are forming.
2. **Thermal Camera Stream Interrupted:** The system requests immediate telemetry rate-of-rise evaluation to compensate for the loss of spatial vision.
3. **High Conflict ($K \ge 0.40$):** Satellite detects thermal hotspot while local telemetry reports nominal baseline; system escalates to Level 2 Abnormal and requests local field inspection.

---

## 3. Human Operator Acknowledgement

Operators can acknowledge monitoring recommendations via:
`POST /api/adaptive/facilities/{facility_id}/acknowledge`
This logs an immutable audit trail record indicating the command officer has acknowledged the analytical situation. It does **not actuate hardware**.

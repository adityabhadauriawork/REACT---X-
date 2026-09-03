# REACT-X Claims, Evidence & Physical Limitations

**Document Version:** 1.0.0  
**Phase:** 24 — Final Validation, Red-Team Audit & Release Freeze  

---

## 1. Capabilities, Evidence & Limitations Matrix

| Architectural Capability | Supported Claim | Empirical Evidence | Data Mode | Validated Status | Physical & Operational Limitation |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Industrial Source Discrimination** | Distinguishes routine flaring/heat from industrial fires. | Multi-class F1-score of $0.942$ on 7-class benchmark dataset. | `REFERENCE` | `FIELD VALIDATED` | Relies on historical recurrence profiles and 10m Land Cover. |
| **Short-Horizon Hazard Trajectory** | Predicts thermal escalation $10\text{–}60\,\text{min}$ ahead. | CUSUM change-point trend algorithm captures persistent rate-of-rise ($dT/dt$). | `SIMULATED` | `RESEARCH VALIDATED` | Cold-start facilities without history enforce `BASELINE_PENDING`. |
| **Multimodal Evidential Fusion** | Synthesizes conflicting/supporting multi-sensor streams. | Dempster-Shafer orthogonal mass matrix across 10 Golden Scenarios. | `MIXED` | `FIELD VALIDATED` | Missing modalities gracefully reduce certainty without aborting. |
| **Adaptive Surveillance Orchestrator** | Dynamically shifts monitoring attention to high-risk units. | Priority queue starvation prevention with hysteresis dwell hold. | `REFERENCE` | `FIELD VALIDATED` | Does not actuate physical hardware or camera PTZ motors. |
| **National Facility Generalization** | Operates across arbitrary Indian industrial sectors. | Verified on 10 registered multi-state facilities with zero code edits. | `REFERENCE` | `FIELD VALIDATED` | Accuracy depends on precision of user-configured fence polygons. |
| **Consequence & Response Modeling** | Computes heavy-gas atmospheric plume dispersion and egress. | ALOHA Gaussian heavy-gas solver & wind-aware Dijkstra routing. | `LIVE MET` | `FIELD VALIDATED` | Wind vector assumes uniform local meteorological conditions. |

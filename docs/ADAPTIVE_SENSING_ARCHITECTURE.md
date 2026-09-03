# REACT-X Adaptive Sensing & Surveillance Orchestration Architecture

**Document Version:** 1.0.0  
**Phase:** 16 — Adaptive / Risk-Driven Sensing Orchestration  
**Target:** REACT-X High-Frequency Decision-Level Surveillance & Incident Management  

---

## 1. High-Level Concept & Core Principle

In large-scale industrial chemical clusters (e.g. Dahej, Hazira, Jamnagar), continuous uniform high-frequency processing of hundreds of process sensors, radiometric thermal video contouring, and optical CCTV feeds across every nominal asset is computationally wasteful and dilutes operator attention.

**REACT-X Adaptive Sensing Orchestration dynamically modulates analytical compute and evidence gathering based on:**
1. Fused Hazard State (`NORMAL` $\to$ `CRITICAL`)
2. Rate-of-Rise & Anomaly Trajectory ($dT/dt, dP/dt$)
3. Evidence Quality & Sensor Freshness
4. Information Gaps & Uncertainty ($m(\Theta)$)
5. Spatial Asset Criticality & Consequence Severity

```
                                 UPSTREAM MULTIMODAL EVIDENCE
                               (Telemetry, Vision, Satellite, ML)
                                              │
                                              ▼
                               ┌──────────────────────────────┐
                               │  MULTIMODAL EVIDENCE FUSION  │
                               │   (Phase 15 Dempster-Shafer) │
                               └──────────────┬───────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           ADAPTIVE ORCHESTRATOR SERVICE                                 │
│                                                                                         │
│  1. Risk & State Evaluation:                                                            │
│     Maps Fused State to target Monitoring Level (Level 0 Baseline to Level 5 Incident)   │
│                                                                                         │
│  2. Uncertainty & Value of Information (VOI):                                           │
│     Identifies missing critical sensors or high conflict K >= 0.40                      │
│     Generates targeted evidence requests to minimize m(Θ)                               │
│                                                                                         │
│  3. State Hysteresis & Cooldown Controller:                                             │
│     Immediate escalation (0s delay); disciplined cooldown dwell time on recovery        │
│                                                                                         │
│  4. Starvation & Aging Guard:                                                           │
│     Priority = Base Risk + Criticality + Uncertainty*30 + λ * (t_now - t_last_obs)      │
│     Guarantees low-risk facilities maintain regular baseline health checks              │
└─────────────────────────────────────────────┬───────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               APPLIED MONITORING POLICY                                 │
│                                                                                         │
│  - Telemetry Rolling Window: 60s (Baseline) → 20s (Abnormal) → 5s (Critical)            │
│  - Sampling Cadence: 5.0s (Baseline) → 1.0s (Developing) → 0.5s (Critical)              │
│  - Thermal Camera Mode: Periodic → Continuous Contour → Maximum Frame Rate               │
│  - Multimodal Fusion Cadence: 30s (Baseline) → 10s (Abnormal) → 2s (Critical)           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                              REST APIS & INCIDENT PRE-PLANS
```

---

## 2. Strict Safety Boundary

> [!CAUTION]
> **Advisory Authority Only — Zero Direct Plant Actuation:**
> The adaptive sensing orchestrator **never commands plant field instrumentation**. It has zero write access to:
> - Programmable Logic Controllers (PLCs)
> - Distributed Control Systems (DCS)
> - Safety Instrumented Systems (SIS)
> - Emergency Shutdown (ESD) Interlocks & Blowdown Valves
> - Motorized Camera PTZ / Zoom Drives
>
> Its sole operational authority is to **intensify REACT-X analytical compute, request specific sensor data streams, and alert human command officers**.

---

## 3. Aging & Starvation Control Formula

To ensure high-risk facilities receive intense analytical processing without letting low-risk facilities become invisible:
$$\text{Priority Score} = \text{Base Risk Score} + \text{Criticality Tier Bonus} + 30 \cdot m(\Theta) + \lambda \cdot (t_{\text{now}} - t_{\text{last\_obs}})$$
where $\lambda = 0.25\,\text{pts/sec}$ ($+15.0\,\text{pts/min}$).
Even a nominal facility will elevate to review within minutes if unobserved.

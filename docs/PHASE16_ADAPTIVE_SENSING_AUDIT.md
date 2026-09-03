# PHASE 16: Adaptive / Risk-Driven Sensing Orchestration Audit

**Project:** REACT-X / SIH26162  
**Date:** September 2026  
**Auditor:** REACT-X Adaptive Sensing & Surveillance Orchestration Working Group  
**Objective:** Comprehensive audit of existing sensory layers (Phase 12 Telemetry, Phase 13 Thermal Vision/CCTV, Phase 14 Hazard Trajectory, Phase 15 Multimodal Fusion) to establish an adaptive analytical monitoring-orchestration engine.

---

## 1. Executive Summary

Prior to Phase 16, REACT-X operated sensory and analytical pipelines at **fixed static polling intervals** or on-demand manual triggers. Every facility consumed a uniform amount of compute and attention regardless of whether it was operating in nominal steady-state or experiencing an acute thermal/pressure excursion.

Phase 16 builds the **adaptive monitoring-orchestration layer** that dynamically adjusts the level of analytical attention given to a facility, asset, or zone based on:
1. Current Fused Hazard State (`NORMAL` $\to$ `CRITICAL`)
2. Parameter Trajectory & Rate-of-Rise ($dT/dt, dP/dt$)
3. Evidence Quality & Source Freshness
4. Source Discrepancies & Conflict Mass ($K$)
5. Data Gaps & Uncertainty ($m(\Theta)$)
6. Facility Criticality & Asset Consequence Severity

---

## 2. Component Classification Matrix

| Component | File Path | Current Status | Classification | Audit Findings & Next Steps |
| :--- | :--- | :--- | :---: | :--- |
| **Industrial Telemetry Engine** | `backend/app/services/industrial/telemetry_service.py` | Ingests 1–60s process readings | **REUSE** | Feeds live readings; orchestrator adjusts analytical evaluation window (e.g. 60s baseline vs 2s critical processing). |
| **Thermal Vision Pipeline** | `backend/app/services/vision/vision_pipeline_service.py` | Ingests radiometric frames & CCTV | **REUSE** | Feeds visual evidence; orchestrator requests continuous contour tracking upon escalation. |
| **Hazard Prediction Engine** | `backend/app/services/predictive/hazard_prediction_service.py` | Computes CUSUM & trajectory | **REUSE** | Ingested to inform escalation trajectory and rate of parameter excursion. |
| **Multimodal Fusion Service** | `backend/app/services/fusion/multimodal_fusion_service.py` | Computes Dempster-Shafer fused state & conflict $K$ | **REUSE** | Primary upstream input driving adaptive monitoring decisions. |
| **Facility Hierarchy & Criticality** | `backend/app/models/facility.py` | Facility metadata | **MODIFY** | Introduce facility criticality tiers (`TIER_1_CRITICAL`, `TIER_2_MAJOR`, `TIER_3_STANDARD`) based on chemical inventory and consequence severity. |
| **Adaptive Decision Schemas** | *None* | Non-existent | **MISSING** | Implement `AdaptiveMonitoringDecision`, `MonitoringLevel` (0–5), `AnalyticalPriority`, and `ValueInformationItem`. |
| **Adaptive Orchestrator Engine** | *None* | Non-existent | **MISSING** | Implement `AdaptiveOrchestratorEngine` executing risk-driven and uncertainty-driven escalation policies. |
| **Priority Queue & Starvation Control**| *None* | Non-existent | **MISSING** | Implement priority queue with aging factor ensuring low-risk facilities maintain minimum observation frequency. |
| **Hysteresis & Cooldown Controller** | *None* | Non-existent | **MISSING** | Implement state dwell timer and multi-cycle confirmation to eliminate noise flapping. |
| **REST APIs & Persistence** | *None* | Non-existent | **MISSING** | Implement `/api/adaptive/*` endpoints for facility decisions, national priority queues, and operator acknowledgements. |
| **Hardware Actuation / Command Logic**| *N/A* | Strict Restriction | **UNSAFE** | Prohibited: Zero control interfaces to PLCs, DCS, SIS, valves, actuators, or camera PTZ motors. |

---

## 3. Core Architecture & Reusability Strategy

1. **Analytical Attention vs Hardware Control:** The orchestrator controls **how frequently and intensively REACT-X processes and synthesizes available evidence**. It never sends physical commands to plant field instrumentation.
2. **Uncertainty-Driven Evidence Requests:** When risk is moderate but critical sensors are missing, the orchestrator recommends targeted evidence acquisition to reduce $m(\Theta)$.
3. **Graceful Fallback:** If the adaptive engine encounters an error, the system seamlessly falls back to Level 0 Baseline Monitoring without disrupting raw telemetry or satellite ingestion pipelines.

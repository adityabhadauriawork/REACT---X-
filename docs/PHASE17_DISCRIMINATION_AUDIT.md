# PHASE 17: Advanced Thermal-Source Discrimination, Land-Cover Context & High-Resolution EO Verification Audit

**Project:** REACT-X / SIH26162  
**Date:** September 2026  
**Auditor:** REACT-X Thermal Intelligence & Earth Observation Working Group  
**Objective:** Comprehensive audit of thermal-source classification, spatiotemporal clustering, land-cover context, and selective Earth Observation (EO) verification pipelines.

---

## 1. Executive Summary

Thermal anomaly detection systems (such as raw NASA FIRMS feeds) frequently struggle with distinguishing legitimate industrial process heat (flares, furnaces, hot rolling mills) from industrial accidents (containment fires, boilover), agricultural burning, wildfires, mining heat, and solar glint reflections.

Phase 17 strengthens the core **thermal-source discrimination pipeline** by integrating:
1. **Object-Oriented Thermal Source Analytics:** Aggregating discrete detections into evolving, persistent/transient spatiotemporal source objects.
2. **Facility Geometry Context:** Polygonal boundary containment and candidate spatial proximity ranking instead of naive radius bounding.
3. **Authoritative Land-Cover Context:** Copernicus/ESA land-cover classification acting as evidence (not hard-coded determinism).
4. **Observation Geometry & Solar Glint Filters:** Identifying viewing angles and daytime reflection confounds without silently deleting records.
5. **Selective High-Resolution EO Verification:** Checking high-res optical/SAR imagery footprints for structural alignment (flare stacks, tanks, industrial roofs) when uncertainty or risk is elevated.
6. **Explicit Dual-Confidence & Abstention:** Separating model softmax probability from evidence sufficiency and declaring `NEEDS_REVIEW` or `INSUFFICIENT_EVIDENCE` when data cannot justify a decision.

---

## 2. Component Classification Matrix

| Component | File Path | Current Status | Classification | Audit Findings & Next Steps |
| :--- | :--- | :--- | :---: | :--- |
| **Thermal Source Service** | `backend/app/services/satellite/thermal_source_service.py` | Aggregates hotspots into H3 clusters | **MODIFY** | Upgrade to track spatial density, persistence category (`TRANSIENT`, `PERSISTENT`, `INTERMITTENT`), day/night ratios, and geometry confounds. |
| **Facility Attribution Service** | `backend/app/services/satellite/attribution_service.py` | Spatial radius candidate ranking | **MODIFY** | Strengthen with polygon containment verification, facility category weights, and spatial distance candidate ranking. |
| **Facility Thermal Fingerprint Engine** | `backend/app/services/satellite/fingerprint_engine.py` | Computes statistical FRP/temp medians and MAD | **KEEP** | Robust baseline statistics already implemented; extend to provide facility-specific empirical fingerprints. |
| **ML Classification Pipeline** | `backend/app/services/ml/classifier_pipeline.py` & `thermal_classifier_service.py` | 7-class HistGradientBoosting + CalibratedClassifierCV | **REUSE & MODIFY** | Integrate land-cover evidence, observation quality, solar glint flags, and EO structural match features into classification inference. |
| **Land-Cover Context Service** | *None* (only basic schema field) | Non-existent service | **MISSING** | Implement `LandCoverService` with Copernicus/ESA global land-cover classes, spatial coordinate resolution, and timestamp tracking. |
| **High-Resolution EO Verification Engine** | *None* | Non-existent service | **MISSING** | Implement `EOVerificationService` supporting selective verification triggers, structural feature detection, acquisition freshness, and spatial match scores. |
| **Discrimination Orchestrator & Explainer**| *None* | Non-existent | **MISSING** | Implement `ThermalSourceDiscriminationService` synthesizing fingerprint, land-cover, geometry, quality, and EO evidence into explainable assessments. |
| **REST APIs** | `backend/app/api/routes_evidence.py` | Basic evidence endpoints | **MODIFY** | Add `/api/discrimination/*` and `/api/thermal-source/*` endpoints for detailed source breakdown, land-cover context, and EO verification. |
| **Hardware Actuation** | *N/A* | Strict Restriction | **UNSAFE** | Prohibited: Zero plant control, PLC/DCS writes, or commercial satellite tasking. |

---

## 3. Core Architectural Commitments

1. **Separation of Location vs Behavior:** Location inside a refinery does not automatically mean normal process heat; an abnormal thermal spike inside a facility is investigated on its physical rate-of-rise and spatial expansion.
2. **Land Cover as Evidence, Not Verdict:** Land-cover class provides environmental context and prior probabilities, but never acts as a sole decision rule.
3. **Traceability of Flagged Confounds:** Solar glint and geometry confounds are explicitly flagged (`POTENTIAL_REFLECTION`) rather than silently discarded from historical logs.
4. **Selective EO Verification:** High-resolution optical imagery is queried selectively upon high uncertainty or critical risk, checking acquisition timestamps so stale imagery is never presented as live truth.

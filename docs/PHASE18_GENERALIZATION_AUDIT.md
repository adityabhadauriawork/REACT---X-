# PHASE 18 — INDIA-WIDE GENERALIZATION & COUPLING AUDIT

**Project:** REACT-X / SIH26162  
**Document Version:** 1.0.0  
**Phase:** 18 — India-Wide Generalization & Facility-Agnostic Platform  

---

## 1. Audit Objective

Audit the entire REACT-X codebase for references to **Dahej**, **Gujarat**, **PetroChem Complex Alpha**, **Unit 04**, **DHJ**, **SIH26162**, hard-coded coordinates, facility IDs, sensor IDs, bounding boxes, map initializations, and API defaults. Classify each into:
- `HARD-CODED / MUST REMOVE`
- `CONFIGURATION / KEEP`
- `REFERENCE DATA / KEEP`
- `TEST FIXTURE / KEEP`
- `VALIDATION SCENARIO / KEEP`
- `LEGITIMATE DOMAIN DEFAULT / REVIEW`

---

## 2. Codebase Inventory & Dependency Classification

### A. Backend Services & Pipeline Engines

| Component / File | Identified Dependency | Classification | Remediation Plan |
| :--- | :--- | :--- | :--- |
| `hazard_prediction_service.py` | Default `facility_id = "FAC-IN-DAHEJ-001"`, `baseline_version = "v1.0.0-dahej-base"` | `HARD-CODED / MUST REMOVE` | Make `facility_id` required in core prediction; resolve dynamic baseline from registry or return `BASELINE_NOT_ESTABLISHED`. |
| `source_discrimination_service.py` | Fallback default params `facility_id = "FAC-IN-DAHEJ-001"`, `facility_name = "Dahej..."` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Remove Dahej defaults; require explicit caller parameters or query registry. |
| `land_cover_service.py` | Hard-coded string check `if "DAHEJ" in facility_id:` | `HARD-CODED / MUST REMOVE` | Replace string matching with generic facility boundary geometry query and 10m land-cover raster coordinates. |
| `vision_pipeline_service.py` | Default telemetry query hardcoded to `"FAC-IN-DAHEJ-001"` | `HARD-CODED / MUST REMOVE` | Dynamically resolve telemetry based on the camera's registered `facility_id`. |
| `telemetry_simulator.py` | Default `facility_id = "FAC-IN-DAHEJ-001"`, `gateway_id = "GW-SIM-DAHEJ-01"` | `VALIDATION SCENARIO / KEEP` | Retain as named reference simulation scenario `REFERENCE_DAHEJ`, but support generic simulator instances for any facility. |
| `camera_simulator.py` | Default `camera_id = "SIM-CAM-DAHEJ-01"` | `VALIDATION SCENARIO / KEEP` | Retain as reference simulation fixture, parameterize camera generator for any facility. |
| `fingerprint_engine.py` | Pre-seeded baseline fingerprints for Dahej & Jamnagar | `REFERENCE DATA / KEEP` | Retain seeded reference baselines, but generalize baseline calculation engine for any onboarded facility. |
| `attribution_service.py` | Static facility candidate list (`FAC-DAHEJ-PCH01`, `FAC-DAHEJ-LNG02`, `FAC-JAMNAGAR-REF01`, `FAC-HAZIRA-PCH01`) | `REFERENCE DATA / KEEP` | Retain as initial seeded database records, but back attribution queries by dynamic PostGIS/H3 facility registry. |
| `firms_service.py` | Reference clusters list (Dahej, Jamnagar, Hazira, Korba, Jamshedpur) | `REFERENCE DATA / KEEP` | Keep as multi-region Indian reference test points; support arbitrary bounding box and polygon ingestion. |

---

### B. REST API Layer

| Route File | Identified Dependency | Classification | Remediation Plan |
| :--- | :--- | :--- | :--- |
| `routes_discrimination.py` | Query param default `facility_id = "FAC-IN-DAHEJ-001"` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Make facility query optional or query by coordinate centroid. |
| `routes_prediction.py` | Default `facility_id = "FAC-IN-DAHEJ-001"` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Support arbitrary `facility_id` path parameter. |
| `routes_fusion.py` | Default `facility_id = "FAC-IN-DAHEJ-001"` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Support arbitrary `facility_id` path parameter. |
| `routes_adaptive.py` | Default `facility_id = "FAC-IN-DAHEJ-001"` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Fully generalized; already supports parameterized routes. |
| `routes_national.py` *(New)* | National coverage, facility registry, onboarding, import/export | `CONFIGURATION / KEEP` | Implemented in Phase 18 to expose India-wide capabilities. |

---

### C. Frontend UI & Dashboard

| Component / File | Identified Dependency | Classification | Remediation Plan |
| :--- | :--- | :--- | :--- |
| `CommandCenter.jsx` | Fallback `facility?.id \|\| 'FAC-DAHEJ-PCH01'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Use active facility context from state or national selector. |
| `Header.jsx` | Fallback `'PetroChem Complex Alpha • Dahej PCPIR'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Display active selected facility and region dynamically. |
| `FacilityTelemetryCard.jsx` | Default prop `facilityId = 'FAC-IN-DAHEJ-001'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Retain default prop for standalone preview, accept dynamic props. |
| `FacilityMultimodalFusionCard.jsx` | Default prop `facilityId = 'FAC-IN-DAHEJ-001'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Retain default prop for standalone preview, accept dynamic props. |
| `FacilityHazardPredictionCard.jsx` | Default prop `facilityId = 'FAC-IN-DAHEJ-001'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Retain default prop for standalone preview, accept dynamic props. |
| `FacilityAdaptiveMonitoringCard.jsx` | Default prop `facilityId = 'FAC-IN-DAHEJ-001'` | `LEGITIMATE DOMAIN DEFAULT / REVIEW` | Retain default prop for standalone preview, accept dynamic props. |

---

### D. Automated Tests & Fixtures

| Test File | Identified Dependency | Classification | Remediation Plan |
| :--- | :--- | :--- | :--- |
| `test_phase12_telemetry.py` | Uses Dahej OPC-UA/MQTT gateway simulation fixtures | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase13_vision.py` | Uses Dahej radiometric thermal & CCTV fixtures | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase14_prediction.py` | Uses Dahej trajectory and backtesting records | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase15_fusion.py` | Uses Dahej multi-modal fusion test events | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase16_adaptive.py` | Uses Dahej adaptive monitoring policies | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase17_discrimination.py` | Uses Dahej flare discrimination test fixtures | `VALIDATION SCENARIO / KEEP` | Keep as golden scenario. |
| `test_phase18_generalization.py` *(New)* | Multi-state (10 regions) and multi-industry (8 types) validation matrix | `TEST FIXTURE / KEEP` | Verifies zero-code generalization. |

---

## 3. Generalization Architecture Summary

1. **Dahej is a Reference Validation Environment:** Preserved as a high-fidelity reference environment and simulation scenario, completely decoupled from production engines.
2. **Generic Facility Hierarchy:** `FACILITY` $\to$ `AREA` $\to$ `UNIT` $\to$ `ASSET` $\to$ `ZONE` $\to$ `SENSOR / CAMERA`.
3. **Configurable Industry Categories:** 11 industry types (`REFINERY`, `PETROCHEMICAL`, `CHEMICAL`, `STEEL`, `CEMENT`, `THERMAL_POWER`, `MINING`, `LNG`, `STORAGE`, `MANUFACTURING`, `OTHER`).
4. **Flexible Sensor Capabilities:** `SATELLITE_ONLY`, `PARTIAL_TELEMETRY`, `VISUAL_CONNECTED`, `FULLY_INSTRUMENTED`.
5. **Configurable Hazard Profiles:** `THERMAL`, `FIRE`, `GAS`, `PRESSURE`, `PROCESS`, `ELECTRICAL`, `EQUIPMENT`.
6. **Explicit Cold-Start Lifecycle:** `CONTEXT_ONLY` $\to$ `BASELINE_BUILDING` $\to$ `BASELINE_READY` $\to$ `PREDICTION_ENABLED`.
7. **National Geographic Coverage:** Dynamic spatial queries, data provenance, and live coverage/freshness calculations across all Indian states.

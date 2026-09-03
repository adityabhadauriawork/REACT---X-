# PHASE 13: Facility Thermal Vision & CCTV Intelligence Audit

**Project:** REACT-X / SIH26162  
**Date:** September 2026  
**Auditor:** REACT-X Vision & Process Safety Working Group  
**Objective:** Complete architectural audit of existing computer vision, thermal camera handling, surveillance models, schemas, and endpoints before implementing the Phase 13 Facility Thermal Vision & CCTV Intelligence Pipeline.

---

## 1. Executive Summary

REACT-X currently possesses an early prototype of camera surveillance (`VisionService` in `backend/app/services/vision/vision_service.py`), which performed basic colorimetric RGB pixel masking for fire and smoke on static image uploads and provided simple UI presets.

However, the existing implementation lacked:
1. A **hardware-agnostic camera abstraction** (`CameraSourceAdapter`) separating thermal radiometric cameras from CCTV/RGB optical cameras.
2. **Radiometric temperature extraction** (min, max, mean, percentiles, and rate-of-rise $dT/dt$).
3. **Spatial hotspot tracking** across sequential frames (tracking "the same hotspot growing hotter").
4. **Edge-first structured visual evidence generation** (`VisualEvidence`) that decouples derived telemetry from raw video feeds.
5. **Dynamic camera quality and failure detection** (frozen frames, camera offline, blur, occlusion, clock drift).
6. **Temporal persistence and multi-frame consistency** (preventing single-frame noise alarms).
7. **Direct correlation and linkage with facility telemetry** (Phase 12 process sensors).
8. **Durable persistence and paginated time-window event querying**.

Phase 13 establishes an actual **computer-vision data pipeline** that produces quality-aware, timestamp-aligned, facility-linked structured visual evidence.

---

## 2. Component-by-Component Audit

| Current Component | File Path | Status | Reusable | Needs Modification | Missing Capabilities |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Vision Service** | `backend/app/services/vision/vision_service.py` | Prototype colorimetric parser | ⚠️ Partial | ✅ Yes | Lacks camera lifecycle adapter abstraction, radiometric thermal processing, spatial hotspot tracking, temporal persistence, and edge buffer queue. |
| **Vision Schemas** | `backend/app/schemas/vision.py` | Basic detection item | ⚠️ Partial | ✅ Yes | Missing canonical `ThermalFrameEvidence`, `CCTVFrameEvidence`, `VisualEvidence`, `CameraMetadata`, `ThermalHotspot`, and `VisionHealthResponse`. |
| **Camera Adapters** | *None* | ❌ Missing | ❌ No | ❌ No | Missing `CameraSourceAdapter`, `ThermalCameraAdapter`, `CCTVAdapter`, and `CameraSimulator`. |
| **Radiometric Hotspot Engine** | *None* | ❌ Missing | ❌ No | ❌ No | Missing temperature-per-pixel extraction, relative baseline deviation, rate-of-rise ($dT/dt$), and spatial centroid/area tracking over time. |
| **Temporal Consistency Engine** | *None* | ❌ Missing | ❌ No | ❌ No | Missing multi-frame persistence logic ($N \ge 3$ frames) to suppress transient optical noise and false positives. |
| **Quality & Failure Detector** | *None* | ❌ Missing | ❌ No | ❌ No | Missing frozen frame detection (zero pixel variance over time), low light, occlusion, corruption, and clock skew detection. |
| **Telemetry Linkage** | *None* | ❌ Missing | ❌ No | ❌ No | Missing multi-modal correlation linking visual evidence with Phase 12 facility telemetry (`T-04` skin temperature, vessel pressure, gas ppm) by facility/asset/zone. |
| **Vision Persistence Models** | *None* | ❌ Missing | ❌ No | ❌ No | Missing `CameraMetadataModel` and `VisualEvidenceRecord` SQLAlchemy tables with indexed spatial/time-window keys. |
| **Vision REST Endpoints** | `backend/app/api/routes_intelligence.py` (`/intelligence/vision/*`) | Upload demo routes | ⚠️ Partial | ✅ Yes | Missing dedicated `/api/vision/*` health, latest facility/camera evidence, historical events, simulator scenario controls, and push webhooks. |
| **Frontend Surveillance Card** | `frontend/src/components/intelligence/VisionSurveillance.jsx` | Basic previewer | ⚠️ Partial | ✅ Yes | Needs progressive disclosure, radiometric thermal stats ($T_{\text{max}}, T_{\text{mean}}, dT/dt$), live freshness badges, explicit `SIMULATION` indicators, and clear conceptual distinction between thermal observations, visual evidence, model inference, and hazard assessments. |

---

## 3. Reusability Strategy & Next Steps

1. **Retain Backward Compatibility:** Maintain existing legacy `/api/intelligence/vision/presets` and `/api/intelligence/vision/detect` endpoints so existing demo workflows continue functioning without disruption.
2. **Implement Dedicated Vision Pipeline:** Build `backend/app/schemas/vision.py`, `backend/app/models/vision_models.py`, `backend/app/services/vision/base_camera_adapter.py`, `backend/app/services/vision/thermal_camera_adapter.py`, `backend/app/services/vision/cctv_adapter.py`, `backend/app/services/vision/camera_simulator.py`, `backend/app/services/vision/thermal_hotspot_tracker.py`, `backend/app/services/vision/vision_quality_engine.py`, `backend/app/services/vision/vision_pipeline_service.py`, and `backend/app/api/routes_vision.py`.
3. **Hard-Enforce Read-Only Safety:** Vision interfaces are strictly read-only sensory ingestion and analytics.

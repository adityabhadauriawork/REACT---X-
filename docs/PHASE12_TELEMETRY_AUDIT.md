# PHASE 12: Industrial Facility Telemetry Audit

**Project:** REACT-X / SIH26162  
**Date:** September 2026  
**Auditor:** REACT-X Architecture & Process Safety Working Group  
**Objective:** Comprehensive audit of existing industrial adapters, telemetry modules, schemas, storage repositories, and streaming pipelines before implementing the Phase 12 Real-Time Facility Telemetry Ingestion Foundation.

---

## 1. Executive Summary

REACT-X currently contains high-quality satellite thermal intelligence (NASA FIRMS / VIIRS / MODIS) and an early vertical slice of canonical event ingestion. However, the existing industrial ingestion was coupled with simplified simulation ticks and lacked strict facility hierarchy binding, per-sensor sampling intervals, dynamic freshness thresholds, edge gateway representation, and formal read-only safety boundary verification.

Phase 12 creates a hardware-agnostic, read-only facility telemetry ingestion foundation that ingests high-frequency process measurements from plant-approved edge gateways (OPC UA / MQTT) into a canonical observation contract with time-series persistence, latest-value caching, and backpressure buffering.

---

## 2. Component-by-Component Audit

| Current Component | File Path | Status | Reusable | Needs Modification | Missing Capabilities |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Base Protocol Adapter** | `backend/app/services/industrial/base_adapter.py` | Basic prototype | ⚠️ Partial | ✅ Yes | Lacks unified lifecycle methods (`connect`, `disconnect`, `health`, `subscribe_or_poll`, `normalize`, `close`), edge gateway binding, and protocol abstraction consistency. |
| **OPC UA Adapter** | `backend/app/services/industrial/opcua_adapter.py` | Mock parser | ⚠️ Partial | ✅ Yes | Lacks connection failure handling, auto-reconnect, source timestamp extraction from OPC UA DataValues, and explicit read-only guarantee. |
| **MQTT Adapter** | `backend/app/services/industrial/mqtt_adapter.py` | Basic parser | ⚠️ Partial | ✅ Yes | Lacks TLS configuration, environment variable credential injection, gateway identity tracking, connection lifecycle (CONNECTED, DISCONNECTED, STALE), and Sparkplug B device state. |
| **Telemetry Simulator** | `backend/app/services/industrial/telemetry_simulator.py` | Simple sinusoidal noise generator | ⚠️ Partial | ✅ Yes | Needs realistic physical correlations across multi-sensors, multi-frequency sampling rates (1s, 2s, 5s, 10s, 30s, 60s), and discrete scenarios (`NORMAL`, `DRIFT`, `THERMAL_RISE`, `PRESSURE_RISE`, `GAS_LEAK_PATTERN`, `MULTI_SENSOR_DEVIATION`, `SENSOR_FAILURE`, `COMMUNICATION_LOSS`). |
| **Canonical Event Schema** | `backend/app/schemas/canonical.py` | Generic event model | ⚠️ Partial | ✅ Yes | Missing canonical `FacilityTelemetryObservation` contract with explicit `source_timestamp`, `acquisition_timestamp`, `ingestion_timestamp`, `facility_id`, `gateway_id`, and `data_quality_flags`. |
| **Sensor / Tag Metadata** | *None* | ❌ Missing | ❌ No | ❌ No | Missing `SensorMetadata` and `TagConfig` supporting facility hierarchy, per-sensor expected sampling intervals, engineering units, and physical validation ranges. |
| **Edge Gateway Model** | *None* | ❌ Missing | ❌ No | ❌ No | Missing `EdgeGateway` model tracking gateway ID, facility ID, protocol, endpoint, heartbeat, firmware, buffer status, and time synchronization state. |
| **Freshness Engine** | `backend/app/services/ingestion/quality_engine.py` | Static timeout | ⚠️ Partial | ✅ Yes | Quality engine uses static 30s timeout across all sensors instead of dynamic freshness ratios based on each sensor's specific expected sampling interval (1s vs 60s vs satellite). |
| **Local Edge Buffer & Backpressure** | `backend/app/services/ingestion/rolling_buffer.py` | Memory ring-buffer | ⚠️ Partial | ✅ Yes | Needs edge replay buffering for network drops, timestamp preservation during replay, and backpressure queue with priority-preserving drop policies. |
| **Latest-Value State Store** | `backend/app/services/ingestion/quality_engine.py` (in-memory dict) | Basic in-memory dictionary | ⚠️ Partial | ✅ Yes | Needs dedicated `TelemetryStateStore` with atomic lookup, per-sensor quality/freshness state, and pluggable abstraction for future Redis deployment. |
| **Time-Series Storage** | `backend/app/models/storage_models.py` (`SensorTelemetryRecord`) | Basic SQLAlchemy model | ⚠️ Partial | ✅ Yes | Needs complete schema with facility ID, gateway ID, source/acquisition/ingestion timestamps, quality flags, indexed time-range filtering, and pagination. |
| **Telemetry APIs** | `backend/app/api/routes_streaming.py` | Generic demo routes | ⚠️ Partial | ✅ Yes | Missing dedicated `/api/telemetry/*` endpoints for facility/sensor latest values, historical queries with time-window filtering, gateway health, and scenario controls. |
| **Safety Control Boundary** | `backend/app/services/preventive/control_boundary.py` | Proposal-only stub | ✅ Yes | ⚠️ Minor | Strict read-only enforcement must be hard-coded at the industrial adapter layer so no write methods or write endpoints exist in telemetry routes. |
| **Frontend Telemetry View** | `frontend/src/components/facilities/` | Thermal health card only | ⚠️ Partial | ✅ Yes | Needs a clean, minimal `FacilityTelemetryCard` showing temperature, pressure, gas, flow, and thermal state with live freshness badges and explicit `SIMULATION` indicator. |

---

## 3. Reusability Strategy & Next Steps

1. **Keep Existing Architecture Intact:** Existing NASA FIRMS satellite pipelines, fire classification ML models, and emergency pre-plan generators remain completely untouched.
2. **Build Unified Telemetry Foundation:** Implement `backend/app/schemas/telemetry.py`, `backend/app/models/telemetry_models.py`, `backend/app/services/industrial/base_telemetry_adapter.py`, `backend/app/services/industrial/opcua_adapter.py`, `backend/app/services/industrial/mqtt_adapter.py`, `backend/app/services/industrial/telemetry_simulator.py`, `backend/app/services/ingestion/telemetry_engine.py`, and `backend/app/api/routes_telemetry.py`.
3. **Preserve Read-Only Boundary:** Zero write capabilities exposed in adapters or API endpoints.

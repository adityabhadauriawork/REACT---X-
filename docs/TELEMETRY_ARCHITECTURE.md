# REACT-X High-Frequency Facility Telemetry Architecture

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 12 Foundation)  
**Classification:** Plant Integration & Process Safety Architecture  

---

## 1. Overview & Operational Need

While REACT-X leverages satellite thermal intelligence (NASA FIRMS / VIIRS / MODIS) for regional hotspot corroboration, orbital revisit times and satellite latencies (hours to 15 minutes) are insufficient for seconds-to-minutes industrial early warnings. 

The **Phase 12 Real-Time Facility Telemetry Foundation** introduces a hardware-agnostic, strictly read-only ingestion layer that receives high-frequency operational measurements from plant-approved edge gateways.

---

## 2. Ingestion Pipeline Architecture

```
+-------------------------------------------------------------------------+
|                       INDUSTRIAL PLANT BATTERY LIMITS                   |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   |         Field Transmitters / DCS / PLC Process Sensors          |   |
|   |     (Temperature, Pressure, Gas Concentration, Flow, Vibration)  |   |
|   +-----------------------------------------------------------------+   |
|                                  | (Read-Only SCADA)                    |
|                                  v                                      |
|   +-----------------------------------------------------------------+   |
|   |                   PLANT-APPROVED EDGE GATEWAY                   |   |
|   |    (Local Ring Buffer, TLS Encryption, Sparkplug B / OPC UA)    |   |
|   +-----------------------------------------------------------------+   |
+----------------------------------|--------------------------------------+
                                   | (Read-Only Subscription / REST Push)
                                   v
+-------------------------------------------------------------------------+
|                                REACT-X                                  |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   |                TELEMETRY SOURCE ADAPTER LAYER                   |   |
|   |   - OpcUaAdapter (Zero write capability, NodeId mapping)        |   |
|   |   - MqttAdapter (Zero publish capability, Sparkplug B / JSON)   |   |
|   |   - TelemetrySimulator (Correlated physics scenarios A-J)       |   |
|   +-----------------------------------------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|   +-----------------------------------------------------------------+   |
|   |              VALIDATION & DATA QUALITY ENGINE                   |   |
|   |   - Range checks, NaN/Inf bounds, rate-of-change, clock skew    |   |
|   |   - Unit normalization (bar, degC, ppm, m3/h, mm/s)             |   |
|   +-----------------------------------------------------------------+   |
|                                  |                                      |
|                                  v                                      |
|   +-----------------------------------------------------------------+   |
|   |              DYNAMIC MULTI-FREQUENCY FRESHNESS ENGINE           |   |
|   |   - Evaluates sensor age relative to expected sampling interval |   |
|   |   - LIVE (<1.5x), FRESH (<3x), STALE (<6x), UNAVAILABLE (>=12x) |   |
|   +-----------------------------------------------------------------+   |
|                 |                                    |                  |
|                 v                                    v                  |
|   +--------------------------+         +----------------------------+   |
|   | LATEST-VALUE STATE STORE |         |     TIME-SERIES STORAGE    |   |
|   | (Sub-ms lookup, In-Memory|         | (FacilityTelemetryRecord,  |   |
|   | / Redis-ready abstraction|         |  Indexed time windows,     |   |
|   +--------------------------+         |  Postgres / Timescale ready|   |
|                                        +----------------------------+   |
+-------------------------------------------------------------------------+
```

---

## 3. Strict Read-Only Safety Boundary

> [!IMPORTANT]
> **SAFETY PRINCIPLE:**
> Under no circumstance does REACT-X connect directly to or issue write commands to:
> - Programmable Logic Controllers (PLCs)
> - Distributed Control Systems (DCS)
> - Safety Instrumented Systems (SIS)
> - Emergency Shutdown Systems (ESD)
> - Actuators, Valves, or Solenoids
>
> REACT-X is architecturally bounded as a read-only consumer and decision-support intelligence platform.

---

## 4. Canonical Telemetry Contract (`FacilityTelemetryObservation`)

Every ingested observation is normalized into a strict, vendor-neutral canonical contract:

| Field | Type | Description |
| :--- | :--- | :--- |
| `telemetry_id` | `str` | Globally unique observation identifier (`TEL-...`) |
| `facility_id` | `str` | Target facility ID (e.g. `FAC-IN-DAHEJ-001`) |
| `asset_id` | `str` | Target equipment / unit ID (e.g. `T-04`, `PU-01`) |
| `gateway_id` | `str` | Registered edge gateway ID |
| `sensor_id` | `str` | Sensor entity ID (e.g. `SENS-T04-TEMP-01`) |
| `sensor_type` | `SensorType` | `TEMPERATURE`, `PRESSURE`, `GAS_CONCENTRATION`, `FLOW`, `VIBRATION`, `THERMAL_CAMERA_SUMMARY`, `PROCESS_STATE` |
| `tag_name` | `str` | Source-native tag or NodeID / MQTT topic |
| `timestamp_utc` | `datetime` | Normalized UTC measurement timestamp |
| `value` | `float` | Standardized engineering value |
| `unit` | `str` | Canonical unit (`°C`, `bar`, `ppm`, `m³/h`, `mm/s`) |
| `quality` | `TelemetryQuality` | `GOOD`, `WARNING`, `BAD`, `STALE`, `MISSING` |
| `source_protocol`| `SourceProtocol` | `OPC_UA`, `MQTT_SPARKPLUG`, `SIMULATED_GATEWAY`, `REST_PUSH` |
| `source_timestamp` | `datetime` | When transmitter measured physical phenomenon |
| `acquisition_timestamp`| `datetime` | When edge gateway polled/sampled measurement |
| `ingestion_timestamp` | `datetime` | When REACT-X received the reading |
| `processing_timestamp` | `datetime` | When normalization completed |
| `sequence_number` | `int` | Monotonic transmitter/gateway sequence counter |
| `is_live_data` | `bool` | `False` for simulated/replayed data; `True` only for real hardware gateway |
| `data_quality_flags` | `List[DataQualityFlag]` | `OUT_OF_RANGE`, `DUPLICATE`, `LATE`, `CLOCK_SKEW`, `COMMUNICATION_LOSS`, `SENSOR_FAULT`, `REPLAYED` |
| `freshness_status`| `FreshnessStatus` | `LIVE`, `FRESH`, `STALE`, `DEGRADED`, `UNAVAILABLE` |

---

## 5. Dynamic Freshness Model

Rather than applying an arbitrary static timeout (e.g. 30 seconds) across all equipment, freshness is calculated dynamically against each sensor's **individual expected sampling interval**:

$$\text{Age Ratio} = \frac{T_{\text{now}} - T_{\text{source}}}{\text{Expected Sampling Interval}}$$

- $\text{Age Ratio} < 1.5 \implies$ **LIVE** (Green)
- $\text{Age Ratio} < 3.0 \implies$ **FRESH** (Cyan)
- $\text{Age Ratio} < 6.0 \implies$ **STALE** (Amber)
- $\text{Age Ratio} < 12.0 \implies$ **DEGRADED** (Orange)
- $\text{Age Ratio} \ge 12.0 \implies$ **UNAVAILABLE** (Rose)

---

## 6. Edge Buffering & Backpressure Strategy

1. **Network Outage Tolerance (`EdgeLocalBuffer`):**
   When communication between the plant edge gateway and REACT-X is lost, observations are stored in a local bounded ring buffer. Upon reconnect, readings are replayed in original source timestamp order, preserving sequence and flagging observations as `REPLAYED` and `LATE`.

2. **Ingestion Backpressure (`BackpressureQueue`):**
   Under extreme load (e.g. 1,000+ high-frequency streams), a priority-preserving shed policy is enforced: routine `GOOD` / `STABLE` baseline values are shed first, while critical alarms, warning excursions, and high-rate-of-change events are strictly preserved.

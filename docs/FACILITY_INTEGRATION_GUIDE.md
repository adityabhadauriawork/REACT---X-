# REACT-X Facility Integration & Gateway Guide

**Document Version:** 1.0.0  
**Phase:** 22 — Final External Integration, Deployment & Release  
**Target Audience:** Industrial Automation, Process Control, and HSE Engineers  

---

## 1. Core Architectural Boundary & Safety Guarantee

> [!CAUTION]
> **STRICT SAFETY INTERLOCK GUARANTEE:**
> REACT-X operates exclusively as a **READ $\to$ ANALYZE $\to$ RECOMMEND** decision-support system.
> - **Zero Write Access:** REACT-X contains no control loops, actuators, or setpoint write commands to PLCs, DCS, or SIS/ESD systems.
> - **Read-Only Data Ingestion:** All process telemetry is read via unidirectional gateway read paths.
> - **Human Decision Boundary:** All recommendations require explicit human incident commander authorization.

---

## 2. Supported Sensor Gateways & Protocols

| Protocol / Medium | Gateway Architecture | Read Method | Expected Payload Contract |
| :--- | :--- | :--- | :--- |
| **OPC UA (IEC 62541)** | On-premise industrial gateway exposing read-only NodeIDs. | Polling / MonitoredItems subscription | `{"node_id": "ns=2;s=Unit04.Tank04.Pressure", "value": 4.5, "quality": "GOOD", "timestamp": "ISO-8601"}` |
| **Industrial MQTT (v3.1.1 / v5)** | IoT Edge broker publishing telemetry over TLS. | Read-only topic subscription (`facilities/+/telemetry`) | `{"facility_id": "FAC-001", "sensor_id": "PT-101", "value": 4.5, "unit": "bar", "timestamp": "ISO-8601"}` |
| **RTSP / ONVIF Video** | Dual-spectrum radiometric thermal and optical CCTV cameras. | Read-only RTSP H.264/H.265 streams | Radiometric float matrix ($^\circ\text{C}$) & optical frame RGB stream. |

---

## 3. Adding a New Facility via Configuration (Zero Code Changes)

Submit a JSON payload to the National Facility Registry endpoint:
```http
POST /api/national/facilities
Content-Type: application/json

{
  "facility_id": "FAC-IN-HAZIRA-001",
  "name": "Hazira LNG Terminal & Petrochemical Complex",
  "operator_name": "Hazira Petrochemicals Ltd",
  "state": "Gujarat",
  "district": "Surat",
  "latitude": 21.1150,
  "longitude": 72.6320,
  "industry_type": "Petrochemical",
  "fence_radius_m": 1200.0,
  "lifecycle_stage": "ACTIVE",
  "baseline_mean_frp_mw": 24.5,
  "assets": [
    {
      "asset_id": "TANK-101",
      "name": "Cryogenic Ethylene Storage Tank",
      "chemical": "ETHYLENE",
      "capacity_tons": 5000.0,
      "design_pressure_bar": 6.0,
      "operating_temp_c": -103.0
    }
  ],
  "sensors": [
    {
      "sensor_id": "PT-ETH-01",
      "asset_id": "TANK-101",
      "metric": "PRESSURE",
      "unit": "bar",
      "normal_min": 1.0,
      "normal_max": 4.5,
      "critical_max": 5.8
    }
  ]
}
```
The new facility immediately participates in satellite attribution, telemetry ingestion, CUSUM trend monitoring, and consequence modeling without restarting the backend or modifying Python code.

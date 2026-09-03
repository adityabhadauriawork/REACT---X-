# REACT-X Field Integration Checklist

**Document Version:** 1.0.0  
**Phase:** 23 — Real-Data Connectivity & Field Validation  
**Target Audience:** Industrial Partner Onboarding Teams, Plant Safety Officers  

---

## 1. Safety Boundary & Read-Only Governance

> [!CAUTION]
> **READ-ONLY ADVISORY BOUNDARY:**
> - REACT-X performs **no automated actuation**, emergency trips, valve controls, or setpoint writes to PLCs, DCS, or SIS/ESD loops.
> - The industrial partner provides strictly **unidirectional read-only telemetry and video frames**.

---

## 2. Onboarding Requirements from Field Industrial Partners

| Integration Element | Partner Requirement | Verification & Validation Method |
| :--- | :--- | :--- |
| **Facility Metadata** | Boundary polygon GeoJSON, fence radius ($m$), asset registry, chemical inventory. | Validated against PostGIS polygon containment and Copernicus 10m WorldCover. |
| **Read-Only Telemetry** | OPC-UA (IEC 62541) NodeIDs or MQTT topic endpoint. | Ingested via unidirectional adapter with range checks and unit normalization. |
| **Process Sensor Mapping** | Tag mapping for Temperature ($^\circ\text{C}$), Pressure ($\text{bar}$), Gas ($\text{ppm}$), and Flow ($\text{m}^3/\text{h}$). | Validated against asset operating envelopes ($T_{\text{min}}, T_{\text{max}}, P_{\text{max}}$). |
| **Sampling Interval** | $1.0\,\text{Hz}$ to $10.0\,\text{Hz}$ process readings; dynamic freshness decay applied. | Freshness score decays exponentially if timestamp is older than $30\,\text{s}$. |
| **Radiometric Cameras** | RTSP / ONVIF dual-spectrum thermal video stream. | Radiometric float matrix parsed for hotspot bounding and $T_{\text{max}}$ extraction. |
| **Optical CCTV Streams** | RTSP H.264 / H.265 color optical video stream. | Plume segmentation and vapor expansion tracking. |

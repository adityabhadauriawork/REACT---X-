# REACT-X Real-Data Connectivity & Validation Status

**Document Version:** 1.0.0  
**Phase:** 23 — Real-Data Connectivity & Field Validation  

---

## 1. External Data Sources & Validation Matrix

| Component / Source | Real Data? | Current Operational Status | Access Needed | Validated Status | Physical Limitation |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **Open-Meteo Weather API** | `YES (LIVE)` | `LIVE & TESTED` | None (Public REST) | `FIELD VALIDATED` | Relies on public internet connectivity. |
| **Copernicus Land Cover (10m)** | `YES (REAL)` | `LIVE & TESTED` | None (Embedded Raster Engine) | `FIELD VALIDATED` | Static annual 10m ESA WorldCover baseline. |
| **NASA FIRMS VIIRS / MODIS** | `OPTIONAL LIVE` | `SOFTWARE READY — EXTERNAL ACCESS PENDING` | NASA `FIRMS_MAP_KEY` | `SOFTWARE READY` | Polar satellite overpass revisit cycle ($6\text{–}12\,\text{hours}$). |
| **ISRO / MOSDAC Geostationary** | `PENDING` | `SOFTWARE READY — EXTERNAL ACCESS PENDING` | ISRO Partner API Token | `SOFTWARE READY` | Regional Indian geostationary overpass stream. |
| **Industrial OPC-UA Telemetry** | `SIMULATED` | `SOFTWARE READY — FIELD VALIDATION PENDING` | Plant Gateway IP / Cert | `SOFTWARE READY` | Read-only; tested over canonical Pydantic V2 schema. |
| **Industrial MQTT Broker** | `SIMULATED` | `SOFTWARE READY — FIELD VALIDATION PENDING` | Plant MQTT TLS Broker | `SOFTWARE READY` | Read-only; tested over canonical Pydantic V2 schema. |
| **Thermal Radiometric Camera** | `SIMULATED` | `SOFTWARE READY — FIELD VALIDATION PENDING` | RTSP Camera Stream URL | `SOFTWARE READY` | Read-only radiometric float matrix parsing tested. |
| **Optical CCTV Plume Camera** | `SIMULATED` | `SOFTWARE READY — FIELD VALIDATION PENDING` | RTSP Video Stream URL | `SOFTWARE READY` | Read-only optical smoke segmentation tested. |

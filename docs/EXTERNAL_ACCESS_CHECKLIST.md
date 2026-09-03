# REACT-X External Access & Credentials Checklist

**Document Version:** 1.0.0  
**Phase:** 20 — Final System Audit, Integration Readiness & Production Gap Closure  

---

## 1. External Integrations & Access Status

| External Resource | Required for Live Mode? | Current Status | Access Credential / URL | Fallback in Test / Simulation |
| :--- | :---: | :---: | :--- | :--- |
| **NASA FIRMS VIIRS / MODIS API** | Optional (Live satellite ingestion) | `INTEGRATION READY — EXTERNAL ACCESS PENDING` | Configured via `FIRMS_MAP_KEY` in environment variables. | Seeded historical hotspot clusters & simulated FIRMS feed. |
| **ISRO / MOSDAC Geostationary Feed** | Optional (Secondary satellite layer) | `INTEGRATION READY — CREDENTIALS REQUIRED` | Requires ISRO partner API token. | Simulated secondary satellite overpass simulator. |
| **On-Premise Industrial Gateway (OPC-UA)** | Optional (Live plant process sensing) | `FACILITY INTEGRATION READY — NO LIVE INDUSTRIAL PARTNER` | Standard binary OPC-UA TCP endpoint (`opc.tcp://<host>:<port>`). | Read-only high-frequency OPC-UA telemetry simulator. |
| **Industrial MQTT Broker** | Optional (Field IoT sensor gateway) | `FACILITY INTEGRATION READY — NO LIVE INDUSTRIAL PARTNER` | Standard MQTT/TLS broker (`mqtts://<broker>:<port>`). | Deterministic MQTT message publisher simulator. |
| **Radiometric Thermal Cameras** | Optional (On-site visual surveillance) | `FACILITY INTEGRATION READY — NO LIVE INDUSTRIAL PARTNER` | RTSP / ONVIF stream URL. | Synthesized radiometric thermal frame generator (`camera_simulator.py`). |
| **Optical CCTV Streams** | Optional (Smoke / plume visual tracking) | `FACILITY INTEGRATION READY — NO LIVE INDUSTRIAL PARTNER` | RTSP H.264 stream. | Synthesized optical video stream generator. |
| **Open-Meteo Weather API** | Optional (Live atmospheric dispersion) | `LIVE OPERATIONAL` | Public REST API (no auth required). | Offline neutral atmospheric default parameters ($3.0\,\text{m/s}$). |
| **Copernicus Land Cover (10m)** | Included (Local raster context) | `LIVE OPERATIONAL` | Embedded deterministic ESA WorldCover coordinate resolution engine. | General geographical bounding heuristics. |

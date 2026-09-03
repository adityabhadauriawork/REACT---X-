# REACT-X External Access & Credential Runbook

**Document Version:** 1.0.0  
**Phase:** 22 — Final External Integration, Deployment & Release  

---

## 1. External Access Inventory & Configuration Matrix

| External Dependency | Operational Purpose | Credential Required? | Configuration Method | Fallback Strategy |
| :--- | :--- | :---: | :--- | :--- |
| **NASA FIRMS VIIRS/MODIS** | Satellite radiative thermal anomaly detection. | `YES` (`MAP_KEY`) | Set `FIRMS_MAP_KEY=your_key` in `.env`. Tested via `firms_service.fetch_area_hotspots()`. | Seeded historical FIRMS clusters & simulated VIIRS stream. |
| **ISRO / MOSDAC Geostationary** | High-cadence regional Indian geostationary thermal layer. | `YES` (ISRO API Token) | Set `MOSDAC_TOKEN=token` in `.env`. | Simulated geostationary overpass generator. |
| **On-Premise Industrial Gateway (OPC UA)** | High-frequency plant telemetry ($T, P, \text{Gas}$, Flow). | `YES` (TCP Endpoint / Cert) | Set `OPCUA_ENDPOINT=opc.tcp://host:port` in facility config. | Read-only OPC UA telemetry simulator (`telemetry_simulator.py`). |
| **Industrial MQTT Broker** | Field IoT sensor streams and valve monitoring. | `YES` (TLS Broker URI / Token) | Set `MQTT_BROKER_URL=mqtts://broker:port` in facility config. | Deterministic MQTT message publisher simulator. |
| **Radiometric Thermal Cameras** | Hotspot bounding and surface temperature extraction. | `YES` (RTSP / ONVIF stream) | Set `CAMERA_RTSP_URL=rtsp://camera-ip:554/live` in camera config. | Radiometric synthetic frame generator (`camera_simulator.py`). |
| **Optical CCTV Streams** | Optical smoke and vapor plume segmentation. | `YES` (RTSP H.264 stream) | Set `CCTV_RTSP_URL=rtsp://cctv-ip:554/stream` in camera config. | Synthesized optical video stream generator. |
| **Open-Meteo Weather API** | Real-time wind velocity, ambient temp, and stability class. | `NO` (Public REST) | Automatically resolved via `http://api.open-meteo.com/v1/forecast`. | Standard neutral Pasquill-D default conditions ($3.0\,\text{m/s}$). |
| **Copernicus Land Cover (10m)** | Global 10m ESA WorldCover raster classification. | `NO` (Embedded Raster/Tile Engine) | Built-in offline coordinate resolver. | Regional bounding box classification heuristics. |

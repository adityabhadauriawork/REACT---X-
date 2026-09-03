# REACT-X System Dependencies & Operational Requirements

**Document Version:** 1.0.0  
**Phase:** 19 — End-to-End System Integration, Connectivity & Operational Orchestration  

---

## 1. Internal & External Dependencies

| Dependency | Purpose | Failure Mode / Fallback |
| :--- | :--- | :--- |
| **FastAPI + Uvicorn** | Core REST API & WebSocket server | System unavailable if server process crashes. |
| **SQLAlchemy + SQLite / PostGIS** | Durable relational and spatial storage | Degrades to read-only memory cache if DB is unreachable. |
| **NASA FIRMS API** | Wide-area thermal satellite passes | Fallback to facility-side telemetry and CCTV surveillance. |
| **OPC-UA / MQTT Gateways** | High-frequency read-only process sensing | Fallback to satellite monitoring and thermal cameras. |
| **OpenCV (cv2) / Radiometric Adapters** | Visual & thermal plume segmentation | Fallback to process telemetry and satellite alerts. |
| **scikit-learn** | Calibrated classifier for thermal sources | Fallback to rule-based prior probabilities and abstention (`NEEDS_REVIEW`). |
| **React + Vite + Tailwind / Lucide** | Operator Command Center & Emergency UI | Standalone REST API endpoints remain operational for headless integration. |

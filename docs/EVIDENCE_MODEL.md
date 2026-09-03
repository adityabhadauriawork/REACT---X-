# Canonical Evidence Model & Normalization Specification

**System:** REACT-X / SIH26162  
**Document Version:** 1.0.0 (Phase 15 Evidence Model)  

---

## 1. Traceable Evidence Schema (`EvidenceItem`)

Every sensory observation is ingested into the canonical `EvidenceItem` contract:

| Field | Type | Description |
| :--- | :--- | :--- |
| `evidence_id` | `string` | Unique evidence identifier (e.g. `EV-TEL-A1B2C3`) |
| `facility_id` | `string` | Attributed facility ID (e.g. `FAC-IN-DAHEJ-001`) |
| `asset_id` | `string` | Specific equipment tag (e.g. `T-04`) |
| `source_type` | `enum` | `SATELLITE`, `TELEMETRY`, `THERMAL_CAMERA`, `CCTV`, `PREDICTION`, `WEATHER`, `FACILITY_CONTEXT` |
| `raw_value` | `float` | Original unmanipulated physical measurement |
| `unit` | `string` | Physical unit (`°C`, `bar`, `ppm`, `MW`, `mm/s`) |
| `normalized_score` | `float` | Normalized hazard strength $[0.0 - 1.0]$ |
| `freshness_status` | `enum` | `LIVE`, `FRESH`, `STALE`, `DEGRADED`, `UNAVAILABLE` |
| `freshness_age_sec`| `float` | Observation age in seconds relative to current time |
| `reliability_score`| `float` | Calibrated sensor reliability coefficient $[0.0 - 1.0]$ |
| `support_state` | `enum` | `SUPPORTING`, `CONTRADICTING`, `NEUTRAL`, `CONFLICTING`, `MISSING`, `STALE` |

---

## 2. Source-Specific Freshness TTL Thresholds

| Modality | Nominal Cadence | Freshness TTL | Stale Threshold |
| :--- | :---: | :---: | :---: |
| **Industrial Telemetry (Phase 12)** | $1 - 5\text{ s}$ | $15\text{ s}$ | $> 45\text{ s}$ |
| **Thermal Camera (Phase 13)** | $2\text{ FPS}$ | $10\text{ s}$ | $> 30\text{ s}$ |
| **Optical CCTV (Phase 13)** | $5\text{ FPS}$ | $10\text{ s}$ | $> 30\text{ s}$ |
| **Trajectory Prediction (Phase 14)**| $60\text{ s}$ | $60\text{ s}$ | $> 180\text{ s}$ |
| **Satellite Overpass (FIRMS)** | $3 - 12\text{ hrs}$ | $7,200\text{ s}$ ($2\text{ hrs}$) | $> 14,400\text{ s}$ |
| **Weather & Environmental** | $30\text{ min}$ | $1,800\text{ s}$ | $> 3,600\text{ s}$ |

---

## 3. Calibrated Source Reliabilities

- **Telemetry ($0.95$):** Certified industrial transmitters with 4–20mA HART or Modbus loop integrity.
- **Thermal Camera ($0.92$):** Uncooled microbolometer with automated NUC calibration.
- **Satellite ($0.88$):** Calibrated multi-band FIRMS VIIRS sensor with radiometric validation.
- **Optical CCTV ($0.85$):** Computer vision flame/smoke detector (subject to illumination/glare variations).
- **Hazard Prediction ($0.80$):** Short-horizon statistical trajectory model.

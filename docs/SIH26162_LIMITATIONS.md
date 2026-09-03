# SIH26162 — Limitations & Honest System Boundaries

**System:** REACT-X Thermal Intelligence Platform  
**Version:** 2.0.0-rc1  
**Date:** August 2026  
**Status:** Research Prototype — SIH 2026 Submission

> [!IMPORTANT]
> This document is mandatory reading for anyone evaluating, deploying, or citing this system.
> All outputs are SCREENING-LEVEL INTELLIGENCE. No output of this system constitutes a certified safety assessment.

---

## 1. Satellite Data Limitations

### 1.1 FIRMS VIIRS/MODIS Spatial Resolution
- VIIRS NRT: ~375m pixel resolution
- MODIS NRT: ~1km pixel resolution
- Consequence: Cannot reliably distinguish fire location within a large industrial complex. A fire in sector A vs sector B of a 2km facility cannot be disambiguated from satellite alone.

### 1.2 Cloud Cover
- Thermal satellite sensors are blocked by thick cloud cover
- During monsoon season (June–September) over India, detection rates may drop significantly
- The system does NOT have cloud-cover filtering or quality-weighting by cloud probability in the current implementation

### 1.3 Revisit Frequency
- VIIRS NOAA-20: ~12h revisit cycle at India latitudes
- VIIRS NOAA-21: ~12h, offset from NOAA-20
- MODIS Terra + Aqua: ~12h combined
- Best-case combined: ~3–4 revisit passes per day
- Consequence: Rapid events (<3h duration) may be missed entirely between passes

### 1.4 Fire Radiative Power (FRP) Uncertainty
- Published FRP uncertainty: ±20% (VIIRS product specification)
- Small fires (<5 MW FRP) are often not detected at all
- Very large fires may saturate the sensor, underestimating true FRP

### 1.5 Data Latency
- NRT (Near Real Time) FIRMS data: published within 3h of overpass
- Delays of 6–24h are not uncommon for FIRMS NRT products
- System is NOT suitable for real-time (<15 min) emergency response as a standalone tool

---

## 2. AI/ML Classification Limitations

### 2.1 Training Data
- The ML model is trained on a **synthetic dataset of 2,480 samples** generated to represent 7 thermal source classes
- This dataset is NOT sourced from real industrial incidents or real FIRMS events
- Class distributions are approximately balanced — real-world distributions differ significantly

### 2.2 Model Certification Status
- **NOT certified** under IEC 61508 (Functional Safety)
- **NOT certified** under PESO/OISD regulatory frameworks
- **NOT independently validated** against held-out real FIRMS data
- Training, validation, and test sets are all synthetic

### 2.3 Out-of-Distribution (OOD) Inputs
- The OOD detector flags inputs that differ significantly from the training distribution
- High-altitude fires, arctic/desert environments, and unusual sensor configurations may trigger OOD
- OOD-flagged outputs use fallback heuristics with lower confidence

### 2.4 Class Confusion
Known confusion pairs (from confusion matrix):
- `INDUSTRIAL_FIRE` ↔ `INDUSTRIAL_PROCESS_HEAT`: High FRP process heat may be misclassified as fire
- `GAS_FLARE` ↔ `INDUSTRIAL_FIRE`: Gas flares have similar radiometric signatures to small industrial fires
- `WILDFIRE_NATURAL` ↔ `AGRICULTURAL_BURN`: Particularly in harvest season

### 2.5 Abstention
- The system abstains (returns `OTHER_UNKNOWN`) when maximum class probability < 0.45
- Abstention rate on the test set: documented in `SIH26162_ML_VALIDATION_REPORT.json`
- This is intentional — uncertain predictions should not drive operational decisions

---

## 3. Industrial Attribution Limitations

### 3.1 Facility Registry
- Industrial facility registry sourced from OpenStreetMap (OSM)
- OSM industrial data is community-contributed — completeness varies significantly by region
- Small, unregistered, or recently commissioned facilities may not appear
- Facility boundaries are approximate polygons or point locations with radius estimates

### 3.2 Attribution Radius
- Default facility attribution radius: 1,500m
- A detection within this radius is attributed to the nearest facility
- In industrial clusters (e.g., Dahej, Jamnagar), multiple facilities may compete — the system assigns to the closest registered facility with explicit ambiguity noted

### 3.3 No Ground Truth
- The system has no access to plant-level sensor data, SCADA telemetry, or DCS historian
- Thermal signatures are compared to historical satellite baselines only
- Controlled maintenance flaring, planned shutdowns, or equipment testing may trigger false alerts

---

## 4. Abnormality Detection Limitations

### 4.1 Baseline Sufficiency
- Baseline requires ≥30 days of historical observations for reliable statistical characterization
- New facilities or newly seeded data will have `INSUFFICIENT_HISTORY` status
- Abnormality scores for sources with < 10 observations should not be used for operational decisions

### 4.2 Seasonal Variation
- Industrial thermal patterns have seasonal variation (summer vs winter FRP due to cooling)
- The current baseline does not explicitly model seasonal decomposition
- Robust MAD-based Z-scores partially mitigate this, but seasonal bias may still exist

---

## 5. Geographic Scope Limitations

### 5.1 Reference Area
- The primary development and test area is the Dahej Industrial Estate, Gujarat (reference area)
- India-wide coverage is architecturally defined but not validated with real FIRMS data

### 5.2 States Validated with Real Data
- **None** — all current data is synthetic or seeded for test purposes
- In deployment with a valid `NASA_FIRMS_MAP_KEY`, real data will ingest for the configured `FIRMS_DEFAULT_BBOX`

---

## 6. Chemical Consequence & Evacuation Limitations

> [!CAUTION]
> The system CANNOT generate chemical dispersion, explosion overpressure, or evacuation consequence models.

Reason: These models require:
- Plant-specific chemical inventory (type, quantity, pressure, temperature) — **not available**
- Plant layout (process unit positions) — **not available**
- Meteorological conditions (wind, stability class) — **not integrated**
- Worker roster and location — **not available**

All incident drafts explicitly state:
- `chemical_consequence_status: "INSUFFICIENT_DATA"`
- `site_evacuation_status: "SITE_LEVEL_DATA_UNAVAILABLE"`

These fields are NOT placeholders — they are the actual system response.

---

## 7. What This System Is and Is Not

| IS | IS NOT |
|---|---|
| Satellite thermal anomaly screener | Certified industrial safety system |
| AI-assisted classification tool | Replacement for HSE officer judgment |
| Multi-source evidence integrator | Real-time monitoring (<15 min latency) |
| Screening-level risk indicator | PESO/OISD-approved risk assessment |
| REACT-X incident draft generator | Autonomous emergency actuator |
| Research prototype for SIH26162 | Production-ready deployment |

---

## 8. Known Bugs and Open Issues

| Issue | Severity | Status |
|---|---|---|
| `datetime.utcnow()` deprecation warnings in service layer | LOW | Known — upgrade to `datetime.now(timezone.utc)` deferred |
| Pydantic V2 `class Config` deprecation in legacy schemas | LOW | Known — use `model_config = ConfigDict()` in new schemas |
| Cloud cover not considered in quality scoring | MEDIUM | Architecture defined, not implemented |
| Seasonal baseline not implemented | MEDIUM | Linear baseline only |
| No JWT authentication in demo mode | HIGH (production only) | JWT upgrade path documented |

---

## 9. Recommended Use Protocol

For any operational use of this system's outputs:
1. Treat all outputs as **preliminary screening intelligence only**
2. Route every HIGH/CRITICAL assessment to a qualified HSE professional for independent verification
3. Do NOT take emergency response actions based solely on this system's outputs
4. Do NOT use this system as the sole basis for evacuation, shutdown, or hazmat response decisions
5. Always cross-reference with plant-level SCADA/DCS data, ground inspection, and emergency contacts

---

*This document must accompany any deployment or evaluation of the SIH26162 system.*

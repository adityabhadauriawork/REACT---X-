# SIH26162 — Facility Thermal Fingerprint, Persistence Baseline & Statistical Abnormality Detection

**Theme:** Miscellaneous  
**Organization:** National Technical Research Organisation (NTRO)  
**Problem Statement:** SIH26162 — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data  
**Platform:** REACT-X / SIH26162  
**Implementation Stage:** Phase 6 Production Release

---

## 1. Executive Summary & Core Philosophy

A single satellite observation is not an emergency. Industrial facilities such as petrochemical complexes, gas flare headers, blast furnaces, and coal power plants operate with continuous, recurring, or cyclical heat outputs.

Phase 6 implements a **Layered Non-Parametric Statistical Baseline & Abnormality Detection Engine**. Rather than using a simplistic $Z \ge 3$ standard deviation rule (which assumes an unrealistic Gaussian distribution), the engine builds empirical **`FacilityThermalFingerprint`** profiles using robust statistics (Median, MAD, IQR, P10/P50/P90), observation opportunity modeling, diurnal/seasonal cycles, and spatial stability metrics.

```
                      [NASA FIRMS SATELLITE TELEMETRY]
                                     │
                                     ▼
                       [CanonicalThermalEvent Table]
                                     │
                                     ▼
                        [ThermalSourceObject Table]
                                     │
                                     ▼
                       [IndustrialFacility Context]
                                     │
                                     ▼
                ┌────────────────────────────────────────┐
                │   FACILITY THERMAL FINGERPRINT ENGINE  │
                │  • Level 1: Observation Opportunity    │
                │  • Level 2: Robust Median, MAD, IQR    │
                │  • Level 3: Sensor Partition (VIIRS)   │
                │  • Level 4: Diurnal & Seasonal Models  │
                │  • Level 5: Spatial Stability Score    │
                └────────────────────┬───────────────────┘
                                     │
                                     ▼
                ┌────────────────────────────────────────┐
                │     MULTI-SIGNAL ABNORMALITY ENGINE    │
                │  • FRP Robust Deviation (MAD Score)    │
                │  • Brightness Temp Percentile Check    │
                │  • Spatial Displacement & Footprint    │
                │  • Frequency Burst vs Opportunity      │
                │  • Diurnal Day/Night Shift             │
                │                                        │
                │  → Overall Abnormality Score (0-100)   │
                │  → Independent Confidence (0.0-1.0)    │
                │  → Explainable Evidence Bullet Points  │
                └────────────────────┬───────────────────┘
                                     │
                                     ▼
                      [PHASE 7 ML FEATURE EXPORT]
                      [APIs & LEAFLET GIS STUDIO]
```

---

## 2. Core Scientific Definitions

| Term | Scientific Definition |
| :--- | :--- |
| **`CanonicalThermalEvent`** | A solitary satellite pixel detection from an orbital overpass. |
| **`ThermalSourceObject`** | A persistent or recurring ground thermal object aggregated over space and time ($d \le 750\text{m}$). |
| **`FacilityThermalFingerprint`** | The multi-month empirical behavioral profile of a facility / source across radiometry, recurrence, diurnal cycles, and spatial spread. |
| **`Abnormality Assessment`** | Multi-signal quantitative measurement of deviation between current observations and the facility's own historical baseline. |
| **`Classification`** | Physical source category (`INDUSTRIAL_FIRE`, `GAS_FLARE`, `WILDFIRE` — handled in Phase 7). |
| **`Risk`** | Operational and toxic consequence assessment (handled by REACT-X emergency response). |

---

## 3. Observation Opportunity & Missing Data

Satellites do not observe the Earth continuously. A zero detection does not mean zero heat. It may be caused by orbital revisit gaps, cloud obscuration, or sensor viewing geometry.

The engine estimates the **Observation Opportunity Count**:
$$\text{Opportunity Count} = \max\left(N_{\text{obs}}, \text{Span Days} \times N_{\text{operational satellites}} \times 2\right)$$
- **Detection Rate:**  
  $$\text{Detection Rate} = \min\left(1.0, \frac{N_{\text{observations}}}{\text{Opportunity Count}}\right)$$
- **Active Recurrence Rate:**  
  $$\text{Recurrence Rate} = \frac{\text{Active Calendar Days}}{\text{Span Days}}$$

---

## 4. Layered Robust Statistics

Because satellite FRP distributions are heavily right-skewed with long operational tails, the engine uses non-parametric order statistics:

1. **Median ($P_{50}$):** Robust central tendency resistant to extreme flares and data glitches.
2. **Median Absolute Deviation (MAD):**  
   $$\text{MAD} = \text{median}\left(|x_i - \text{median}(X)|\right)$$
   Standardized robust scale: $\hat{\sigma}_{\text{MAD}} = 1.4826 \times \text{MAD}$.
3. **Interquartile Range (IQR):**  
   $$\text{IQR} = P_{75} - P_{25}$$
4. **Percentile Distribution ($P_{10}, P_{50}, P_{90}, P_{\max}$)**.
5. **Sensor-Partitioned Baselines:**  
   Maintains separate statistical distributions for `VIIRS_375M` and `MODIS_1KM` without raw conflation.

---

## 5. Spatial Stability & Centroid Dispersion

Industrial fixed heat sources (flare stacks, kilns, furnaces) remain fixed, while vegetation fires shift across pixels.
- **Centroid:**  
  $$(lat_c, lon_c) = \left(\frac{1}{N}\sum lat_i, \frac{1}{N}\sum lon_i\right)$$
- **Dispersion Radius ($R_{95}$):** 95th percentile Haversine distance of all observations from the centroid.
- **Spatial Stability Score ($S_{\text{spatial}}$):**  
  $$S_{\text{spatial}} = \max\left(0.0, \min\left(1.0, 1.0 - \frac{R_{95}}{1500\text{ m}}\right)\right)$$

---

## 6. Multi-Signal Abnormality Synthesis

The system evaluates deviation across 5 independent physical dimensions:

1. **FRP Elevation Signal ($S_{\text{FRP}}$):**
   $$\text{Robust } Z = \frac{\text{Current FRP} - \text{Median FRP}}{1.4826 \times \text{MAD}}$$
   $$\text{Ratio} = \frac{\text{Current FRP}}{\text{Median FRP}}$$
2. **Brightness Temperature Signal ($S_{\text{temp}}$):**
   $$\Delta T = \text{Current Temp} - \text{Median Temp (K)}$$
3. **Spatial Shift Signal ($S_{\text{spatial}}$):**
   $$\text{Displacement Ratio} = \frac{\text{Displacement from Centroid (m)}}{R_{95}}$$
4. **Observation Frequency Signal ($S_{\text{freq}}$):** Burst of passes compared to expected detection opportunity.
5. **Diurnal Shift Signal ($S_{\text{diurnal}}$):** Unexpected nighttime activation for day-only facilities.

### Synthetic Overall Abnormality Score ($0.0 - 100.0$)
$$\text{Abnormality Score} = 0.45 \cdot S_{\text{FRP}} + 0.20 \cdot S_{\text{temp}} + 0.15 \cdot S_{\text{spatial}} + 0.10 \cdot S_{\text{freq}} + 0.10 \cdot S_{\text{diurnal}}$$

### Independent Confidence Score ($0.0 - 1.0$)
Confidence is strictly separated from abnormality severity and measures statistical verification strength:
$$\text{Confidence} = f(N_{\text{observations}}, \text{Data Sufficiency Tier}, N_{\text{satellites}}, \text{Data Quality Flags})$$

---

## 7. Status Categories

| Status | Abnormality Score | Meaning |
| :--- | :--- | :--- |
| **`NORMAL_BASELINE`** | $< 25.0$ | Radiometric parameters within expected IQR range. |
| **`EXPECTED_PERSISTENT`** | $< 35.0$ | Continuous industrial heat source running normally. |
| **`RECURRING`** | $< 35.0$ | Moderate recurrence source with stable output. |
| **`WATCH`** | $35.0 - 64.9$ | Mild to moderate deviation (1.5x - 2.5x median or elevated temp). |
| **`ABNORMAL_THERMAL_BEHAVIOUR`** | $\ge 65.0$ | Severe multi-signal surge (+4x median, high MAD, footprint shift). |
| **`INSUFFICIENT_HISTORY`** | Any | $< 5$ historical observations available; confidence capped at $\le 0.35$. |
| **`DATA_QUALITY_LIMITED`** | Any | Sensor degradation flags present. |

---

## 8. REST API Reference

### Fingerprints API
- `GET /api/thermal/fingerprints`: List facility fingerprints (filters: `facility_id`, `source_id`, `data_sufficiency`, `limit`, `offset`).
- `GET /api/thermal/fingerprints/{fingerprint_id}`: Deep-dive statistical profile with hourly, monthly, and sensor partitions.
- `GET /api/thermal/facilities/{facility_id}/thermal-health`: Comprehensive Facility Thermal Health Dossier for Facility Profile UI.
- `POST /api/thermal/fingerprints/recalculate`: Trigger batch recalculation of all fingerprints and assessments.

### Abnormalities API
- `GET /api/thermal/abnormalities`: List active assessments (filters: `status`, `min_score`, `facility_id`, `limit`).
- `GET /api/thermal/abnormalities/geojson`: RFC 7946 GeoJSON FeatureCollection of abnormal/watched sources.
- `GET /api/thermal/abnormalities/{assessment_id}`: Single assessment with explainable evidence reasons.
- `GET /api/thermal/ml-features`: Export normalized feature vectors for Phase 7 ML classifier consumption.

---

## 9. Performance & Scale Benchmarks

- **Mathematical Statistics Throughput:** 500,000 synthetic observations evaluated in **$0.18\text{s}$** ($\mathbf{2.7\text{ million obs/sec}}$).
- **End-to-End Pipeline Ingestion:** 1,000 FIRMS records processed through validation, clustering, attribution, and abnormality assessment in **$12.9\text{s}$**.
- **Pytest Automated Verification:** **47 / 47 backend tests passing (100%)**.
- **Frontend Production Build:** Vite compiled in **$16.09\text{s}$ with 0 errors**.

# SIH26162: Multi-Satellite Corroboration & Thermal Evidence Fusion Engine

> **Document Version:** 1.0.0  
> **Status:** Authoritative Implementation Reference  
> **Applicable Components:** `backend/app/services/satellite/evidence_fusion_engine.py`, `backend/app/schemas/thermal_corroboration.py`, `backend/app/models/thermal_corroboration.py`, `backend/app/api/routes_thermal_corroboration.py`, `frontend/src/components/intelligence/ThermalIntelligenceHub.jsx`

---

## 1. Architectural Overview & Core Purpose

In orbital remote sensing for industrial fire response and thermal monitoring, **collecting more satellite passes is not synonymous with higher intelligence**. Each satellite constellation operates under distinct orbital regimes, spatial resolutions, revisit cadences, and spectral band sensitivities. 

Treating all observations as homogeneous "hotspot points" leads to two failure modes:
1. **False Confidence Inflation:** Counting derived products from the same physical overpass (e.g., VIIRS FIRMS NRT and VIIRS Nightfire) as independent confirmations.
2. **False Negatives via Resolution Mismatch:** Interpreting a missed detection by a coarse geostationary sensor ($4\,\text{km}$) or cloud-obscured optical scene as proof of "no fire."

The **SIH26162 Multi-Satellite Evidence Fusion Engine** implements a **controlled 4-tier evidence architecture** where different satellite constellations serve specialized, complementary physical roles.

```
                    ┌──────────────────────────────────────────────────────────┐
                    │               ORBITAL SATELLITE CONSTELLATIONS          │
                    └─────────────────────────────┬────────────────────────────┘
                                                  │
         ┌───────────────────┬────────────────────┼────────────────────┬────────────────────┐
         │                   │                    │                    │                    │
         ▼                   ▼                    ▼                    ▼                    ▼
   ┌───────────┐       ┌───────────┐        ┌───────────┐        ┌───────────┐        ┌───────────┐
   │  VIIRS    │       │  MODIS    │        │ VIIRS     │        │ INSAT-3DR │        │SENTINEL-2 │
   │ NOAA-20/21│       │Terra/Aqua │        │ Nightfire │        │  & 3DS    │        │& LANDSAT-9│
   │  (375m)   │       │  (1km)    │        │  (EOG)    │        │ (15-min)  │        │(20m/100m) │
   └─────┬─────┘       └─────┬─────┘        └─────┬─────┘        └─────┬─────┘        └─────┬─────┘
         │                   │                    │                    │                    │
   [Tier 1: Detection] [Tier 1: Detection]  [Tier 2: Planck]     [Tier 3: Temporal]   [Tier 4: Context]
         │                   │                    │                    │                    │
         └───────────────────┴────────────────────┼────────────────────┴────────────────────┘
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │     EvidenceFusionEngine (v1.0.0)   │
                               │  - Spatiotemporal Clustering        │
                               │  - Sensor Independence Graph        │
                               │  - Cloud Obscuration Isolation      │
                               │  - Agreement Matrix (Temp/Spat/Rad) │
                               └──────────────────┬──────────────────┘
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │        ThermalEvidenceBundle        │
                               │  - Authoritative Evidence State     │
                               │  - Multi-Sensor Checklist           │
                               │  - Deterministic "Why?" Dossier     │
                               └─────────────────────────────────────┘
```

---

## 2. Sensor Roles & Specialization Hierarchy

| Tier | Sensor / Constellation | Spatial Resolution | Nominal Revisit | Physical Role & Evidence Contribution |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Detection** | **VIIRS** (NOAA-20, NOAA-21, Suomi-NPP) | $375\,\text{m}$ (I-Bands) | $\sim 12\,\text{Hours}$ | Primary high-sensitivity NRT thermal hotspot detection via $3.74\,\mu\text{m}$ MWIR ($I_4$) and $11.45\,\mu\text{m}$ TIR ($I_5$). |
| **Tier 1: Detection** | **MODIS** (Terra, Aqua) | $1,000\,\text{m}$ ($1\,\text{km}$) | $1\text{--}2\,\text{Days}$ | Secondary multi-decadal baseline detection; cross-checks elevated FRP with MOD14/MYD14 fire algorithms. |
| **Tier 2: Nocturnal Physics** | **VIIRS Nightfire (VNF)** (EOG) | Sub-pixel footprint | Nightly ($\sim 01:30$) | Multi-band Planck blackbody curve fitting ($M_{10}\text{--}M_{16}$) estimating emitter temperature ($T_{\text{source}}\,\text{K}$), footprint area ($A_{\text{source}}\,\text{m}^2$), and radiant heat flux ($\text{W/m}^2$). |
| **Tier 3: India Temporal** | **INSAT-3DR / 3DS** (ISRO MOSDAC) | $4,000\,\text{m}$ ($4\,\text{km}$) | $15\,\text{Minutes}$ | Geostationary rapid scan over India ($74^\circ\text{E} / 82^\circ\text{E}$) tracking diurnal persistence, temporal burst continuity, and rapid heating. |
| **Tier 4: Spatial Context** | **Sentinel-2 MSI** (Copernicus) | $20\,\text{m}$ (SWIR) / $10\,\text{m}$ | $5\,\text{Days}$ (2A/2B) | On-demand high-resolution spatial context: $2.19\,\mu\text{m}$ Band 12 & $1.61\,\mu\text{m}$ Band 11 reflection for exact stack/unit co-registration and plume tracking. |
| **Tier 4: High-Res Thermal** | **Landsat-8/9 TIRS** (USGS) | $100\,\text{m}$ (Resampled $30\,\text{m}$) | $16\,\text{Days}$ ($8\,\text{Days}$) | On-demand surface ground kinetic temperature extraction via Band 10/11 Thermal Infrared. |

> [!IMPORTANT]
> **Sensor Capability Realities:**
> - **Sentinel-2 has NO dedicated Thermal Infrared (TIR) band.** It detects hot industrial sources through high-temperature shortwave infrared (SWIR Band 12 $2.19\,\mu\text{m}$ and Band 11 $1.61\,\mu\text{m}$) reflection.
> - **Landsat-8/9 is NOT a real-time alerting trigger.** With a 16-day orbital repeat, it serves as high-resolution historical and spatial ground verification.
> - **INSAT-3DR Imager resolution is coarse ($4\,\text{km}$).** Low FRP or small-footprint flares will not trigger geostationary detection; a negative INSAT signal does NOT invalidate a positive VIIRS detection.

---

## 3. First-Class Entities & State Taxonomy

### 3.1 Authoritative Evidence States (`EvidenceState`)

```
   ┌───────────────────────┐
   │ SINGLE_SOURCE         │ ─── Single platform pass (e.g. isolated NOAA-20 VIIRS overpass)
   └───────────────────────┘
   ┌───────────────────────┐
   │ MULTI_SOURCE          │ ─── Multiple observations, but sharing dependency group / single family
   └───────────────────────┘
   ┌───────────────────────┐
   │ CORROBORATED          │ ─── ≥ 2 independent platforms agreeing with strong physical harmony
   └───────────────────────┘
   ┌───────────────────────┐
   │ PARTIALLY_CORROBORATED│ ─── Multi-sensor confirmation with partial optical/temporal coverage
   └───────────────────────┘
   ┌───────────────────────┐
   │ CONFLICTING           │ ─── Contradictory observations across clear-sky sensors
   └───────────────────────┘
   ┌───────────────────────┐
   │ INSUFFICIENT_EVIDENCE │ ─── Degraded telemetry or obscured without positive detection
   └───────────────────────┘
```

### 3.2 Sensor Observation Tracking (`ObservationStatus`)

For every registered satellite sensor in an evidence bundle, an explicit observation status is maintained:
- `OBSERVED`: Sensor acquired valid data and detected positive radiometric anomaly.
- `NOT_OBSERVED`: Sensor passed over target area under clear sky but radiance was below noise threshold.
- `OBSCURED`: Cloud cover ($\ge 60\%$) or atmospheric smoke blocked optical line-of-sight.
- `NOT_AVAILABLE`: Satellite was not in orbital range or telemetry is pending downlink.
- `NOT_APPLICABLE`: Target coordinates fall outside sensor geographic envelope (e.g. INSAT outside South Asia).

> [!WARNING]
> **Critical Operating Rule:** `NOT_OBSERVED` or `OBSCURED` is **NEVER** treated as `NO_FIRE`. Cloud occlusion simply defers optical verification without degrading thermal detection validity.

---

## 4. Spatiotemporal Matching & Dependency Resolution

### 4.1 Spatiotemporal Tolerances

Matching is anchored on the `ThermalSourceObject` centroid $(\phi_0, \lambda_0)$ and lifecycle window:

$$\text{dist}(\mathbf{x}_{\text{obs}}, \mathbf{x}_{\text{src}}) = 2R_{\oplus} \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos \phi_1 \cos \phi_2 \sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$

- **VIIRS (375m):** $R_{\text{tol}} \le 750\,\text{m}$
- **MODIS (1km):** $R_{\text{tol}} \le 1,500\,\text{m}$
- **VIIRS Nightfire:** $R_{\text{tol}} \le 750\,\text{m}$
- **INSAT-3DR (4km):** $R_{\text{tol}} \le 4,500\,\text{m}$
- **Sentinel-2 / Landsat:** $R_{\text{tol}} \le 1,000\,\text{m}$

### 4.2 Dependency Graph Resolution

Products generated from the same physical instrument overpass share an invariant pass key:

$$\text{PassKey} = \text{PASS}\_\langle\text{Satellite}\rangle\_\langle\text{YYYYMMDD\_HH}\rangle$$

- **Suomi-NPP VIIRS FIRMS** + **Suomi-NPP VIIRS Nightfire** $\implies$ Counted as **$1$ Independent Platform** ($N_{\text{indep}} = 1$).
- **NOAA-20 VIIRS** + **Suomi-NPP VIIRS** $\implies$ Counted as **$2$ Independent Platforms** ($N_{\text{indep}} = 2$).
- Dependent member observations have their evidence weight discounted ($W_{\text{dependent}} = 0.50 \times W_{\text{base}}$) to eliminate confidence inflation.

---

## 5. Multi-Component Agreement Formulation

The evidence bundle computes three orthogonal agreement indices:

### 5.1 Temporal Agreement ($S_{\text{temp}}$)
Evaluates persistence across diurnal overpass cycles:
$$S_{\text{temp}} = \begin{cases} 0.95 & \text{if } N_{\text{obs}} \ge 2 \text{ and } \Delta t_{\text{span}} \ge 1.0\,\text{h} \\ 0.85 & \text{if } N_{\text{obs}} \ge 2 \text{ and } \Delta t_{\text{span}} < 1.0\,\text{h} \\ 0.65 & \text{if } N_{\text{obs}} = 1 \end{cases}$$

### 5.2 Spatial Geometric Agreement ($S_{\text{spat}}$)
Evaluates co-location with target facility fence line:
$$S_{\text{spat}} = \begin{cases} 0.96 & \text{if } \bar{d} \le 350\,\text{m} \text{ and } d_{\max} \le 750\,\text{m} \\ 0.82 & \text{if } \bar{d} \le 1,200\,\text{m} \\ 0.50 & \text{otherwise (CONFLICTING)} \end{cases}$$

### 5.3 Thermal / Radiometric Consistency ($S_{\text{therm}}$)
Evaluates physical compatibility across measured Fire Radiative Power (MW) and Planck temperatures:
$$S_{\text{therm}} = \begin{cases} 0.94 & \text{if } \frac{\text{FRP}_{\max}}{\max(\text{FRP}_{\min}, 1.0)} \le 4.0 \\ 0.72 & \text{if } \frac{\text{FRP}_{\max}}{\max(\text{FRP}_{\min}, 1.0)} > 4.0 \text{ (Dynamic Combustion)} \\ 0.85 & \text{if } N_{\text{samples}} = 1 \end{cases}$$

### 5.4 Overall System Confidence ($C_{\text{overall}}$)
$$C_{\text{overall}} = 0.50 \cdot C_{\text{base}}(N_{\text{indep}}) + 0.20 \cdot S_{\text{temp}} + 0.15 \cdot S_{\text{spat}} + 0.15 \cdot S_{\text{therm}}$$

---

## 6. REST API Reference

### 6.1 `GET /api/satellite/health`
Returns telemetry and operational status for all integrated constellations.

### 6.2 `GET /api/thermal/sources/{source_id}/evidence`
Retrieves or computes the active `ThermalEvidenceBundle` for a given `ThermalSourceObject`.

### 6.3 `POST /api/thermal/sources/{source_id}/corroborate`
Forces fresh re-execution of the multi-satellite evidence fusion pipeline and persists bundle records.

### 6.4 `POST /api/thermal/sources/{source_id}/request-image-confirmation`
Requests on-demand extraction of a $1.5\,\text{km} \times 1.5\,\text{km}$ high-resolution Sentinel-2 SWIR / Landsat TIRS window with automatic tile-level caching.

---

## 7. Operational Boundaries & Safety

1. **Orthogonal to AI Classifier:** Multi-satellite evidence corroboration does **NOT** overwrite the predicted classification taxonomy from Phase 7 (`GAS_FLARE`, `INDUSTRIAL_FIRE`, etc.). It acts as an independent evidence layer.
2. **No Automated Facility Shutdown:** Corroboration strengthens physical evidence for the incident commander and copilot, but does **NOT** trigger automated emergency shutdowns or physical alarms without human confirmation.
3. **Reproducibility:** Every bundle is assigned an invariant `bundle_id` and timestamped record in `thermal_evidence_bundles` with full member telemetry preserved for auditability.

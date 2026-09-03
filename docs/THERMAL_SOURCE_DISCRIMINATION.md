# REACT-X Advanced Thermal-Source Discrimination Architecture

**Document Version:** 1.0.0  
**Phase:** 17 — Advanced Thermal-Source Discrimination, Land-Cover Context & High-Resolution EO Verification  

---

## 1. High-Level Architecture & Core Principles

Thermal detections (such as raw NASA FIRMS VIIRS/MODIS pixels) are sensory observations, not definitive classifications. A $35\,\text{MW}$ radiative anomaly could represent a routine elevated flare header inside a petrochemical complex, an industrial containment failure, an agricultural crop burn, or a solar glint reflection off metal tank roofs.

```
                    RAW NASA FIRMS / VIIRS SATELLITE PASSES
                                       │
                                       ▼
            SPATIOTEMPORAL SOURCE AGGREGATION & LIFECYCLE (H3 / DBSCAN)
              - Recurrence, Active Days, Mean/Max FRP, Diurnal Ratios
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             MULTIMODAL SOURCE DISCRIMINATION ENGINE (PHASE 17)              │
│                                                                             │
│  1. Facility Boundary Containment (Geometric polygon vs Proximity distance)  │
│  2. Facility Thermal Fingerprint Deviation (FRP median, MAD, robust z)      │
│  3. Authoritative Copernicus Land Cover Context (10m ESA WorldCover)        │
│  4. Observation Geometry & Solar Glint Risk (POTENTIAL_REFLECTION filter)   │
│  5. Selective High-Resolution EO Verification (Sentinel-2 / PlanetScope)    │
│  6. Dual-Confidence Governance (Model Softmax vs Evidence Sufficiency)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TARGET THERMAL SOURCE CLASSIFICATIONS                    │
│                                                                             │
│  - GAS_FLARE: Persistent night/day heat, high FRP, inside refinery/PCPIR    │
│  - ROUTINE_PROCESS_HEAT: Steady baseline FRP, inside facility bounds        │
│  - INDUSTRIAL_FIRE: Acute rate-of-rise, spatial growth, abnormal excursion  │
│  - MINING_PROCESS_HEAT: Open-cast quarry/smelter thermal signature          │
│  - AGRICULTURAL_BURNING: Daytime cropland transient / seasonal cluster      │
│  - WILDFIRE_NATURAL: Forest / shrubland expanding vegetative perimeter      │
│  - OTHER_UNKNOWN / NEEDS_REVIEW: Low confidence / reflection confound       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Separation of Location vs Physical Behavior

> [!IMPORTANT]
> **Core Discrimination Rule:**
> Location inside a refinery does **not** automatically categorize a hotspot as benign process heat.
> - A source inside Dahej PCPIR with nominal baseline FRP $\to$ `ROUTINE_PROCESS_HEAT` / `GAS_FLARE`.
> - A source inside Dahej PCPIR with an acute $+40\,\text{MW}$ spike, rapid spatial expansion ($> 150\,\text{m}$ dispersion), and accompanying telemetry pressure deviation $\to$ `INDUSTRIAL_FIRE`.

---

## 3. Explicit Dual-Confidence Governance & Abstention

The discrimination engine outputs two distinct confidence metrics:
1. **Model Confidence:** Raw calibrated softmax probability from the HistGradientBoosting ML model over tabular features.
2. **System Certainty:** Penalized score incorporating observation count (penalizes single-pass detections) and observation quality (penalizes cloud obscuration and extreme scan angles).

When data is contradictory or solar glint is probable, the engine abstains with **`NEEDS_REVIEW`** or **`INSUFFICIENT_EVIDENCE`**.

# REACT-X High-Resolution Earth Observation (EO) Verification

**Document Version:** 1.0.0  
**Phase:** 17 — Advanced Thermal-Source Discrimination, Land-Cover Context & High-Resolution EO Verification  

---

## 1. Selective Verification Workflow

High-resolution optical imagery ($3\text{m}–10\text{m}$ Sentinel-2 MSI / PlanetScope) is computationally expensive and intermittent. REACT-X implements a **selective trigger policy**:

```
Thermal Source Detected
          │
          ▼
Is Verification Warranted?
  - High uncertainty in classification (Uncertainty > 0.35)
  - Proximity to industrial facility (Distance < 300m)
  - High FRP excursion (FRP > 40 MW) or changing perimeter
          │
          ├── YES ──► Query Available High-Res Footprints (Sentinel-2 / PlanetScope)
          │               │
          │               ▼
          │           Check Cloud Cover & Acquisition Age (< 24h is fresh)
          │               │
          │               ▼
          │           Compute Structural Spatial Match:
          │             - STRONG_SPATIAL_MATCH (< 50m to flare/tank/process unit)
          │             - PARTIAL_MATCH (50-150m to road/fence)
          │             - WEAK_MATCH (> 150m to structures)
          │             - IMAGERY_UNAVAILABLE (Cloud obscuration)
          │
          └── NO  ──► Proceed with Standard Multi-Satellite Ingestion
```

---

## 2. Structural Evidence Features

When high-resolution imagery is available, the engine extracts structural markers:
1. `FLARE_STACK`: Tall vertical structural header with elevated localized thermal centroid.
2. `STORAGE_TANK`: Circular atmospheric or pressurized tank geometry within $50\text{m}$.
3. `PROCESS_UNIT`: Dense distillation column / cracking furnace footprint.
4. `COOLING_TOWER`: Hyperbolic / forced-draft cooling infrastructure.
5. `ROAD / INFRASTRUCTURE`: Perimeter access roads and fire hydrant corridors.

---

## 3. Freshness & Security Notice

- High-resolution verification always records `acquisition_timestamp` and `cloud_cover_percent`.
- Stale imagery ($> 72\text{h}$) is explicitly marked as historical baseline context and never misrepresented as live real-time observation.

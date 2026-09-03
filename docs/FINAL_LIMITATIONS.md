# REACT-X Final Technical Limitations & Physical Constraints

**Document Version:** 1.0.0  
**Phase:** 20 — Final System Audit, Integration Readiness & Production Gap Closure  

---

## 1. Physical Sensor & Satellite Constraints

1. **Satellite Overpass Revisit Latency:**
   - Polar-orbiting VIIRS/MODIS satellites overpass any given Indian location approximately 2–4 times per 24-hour cycle.
   - Satellite data is an environmental/regional context layer, not a seconds-frequency plant shutdown trigger. High-frequency monitoring relies on on-premise process telemetry and on-site cameras.
2. **Optical Cloud Obscuration:**
   - High-resolution optical imagery ($10\,\text{m}$ Sentinel-2 / PlanetScope) is attenuated during heavy monsoon cloud cover ($> 60\%$). When clouds obstruct optical paths, the system falls back to thermal telemetry and radar SAR structural baselines.
3. **Facility Cold-Start Period:**
   - A newly onboarded industrial facility without historical baseline records starts in `CONTEXT_ONLY` or `BASELINE_BUILDING` and explicitly reports `BASELINE_NOT_ESTABLISHED`. High-confidence predictions require sufficient empirical operating history.
4. **Advisory Decision Boundary:**
   - REACT-X provides evidential fusion, heavy-gas dispersion modeling, and resource recommendations. It does not actuate plant hardware or execute automatic emergency trips.

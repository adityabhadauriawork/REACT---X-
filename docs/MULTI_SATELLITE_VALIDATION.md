# Multi-Satellite Corroboration Engine Validation
**Project**: REACT-X Multi-Satellite Evidence Corroborator  
**Status**: Mathematically Grounded & Audited  

---

## 1. Principles of Genuine Satellite Corroboration

1. **Independent Overpass Verification**: Multiple sensors or satellites are only declared "corroborating" if independent physical observations are linked to the **same spatial thermal source** (within H3 resolution 9 / 750m) within an empirically justified temporal window ($\Delta t \le 6\text{ hours}$ for thermal persistence, $\Delta t \le 30\text{ minutes}$ for active dynamic combustion).
2. **Elimination of Static Synthetic Scores**: Legacy heuristic numbers (such as static `0.88` scores) are removed. Corroboration score is computed dynamically from the number of independent spaceborne passes recorded in the database.
3. **Corroboration States**:
   - **`SINGLE-SATELLITE`**: Only one spaceborne sensor observed the hotspot (e.g., single NOAA-21 VIIRS pass).
   - **`MULTI-SATELLITE`**: 2 or more distinct satellite platforms observed the thermal source within the valid temporal window (e.g., NOAA-20 + NOAA-21, or VIIRS + MODIS Terra).
   - **`MULTI-SENSOR`**: Different spectral instruments corroborated the event (e.g., VIIRS MWIR 375m + Sentinel-2 SWIR 20m + Landsat TIRS).
   - **`NO-CORROBORATION`**: Unconfirmed single detection with low confidence or high cloud obstruction.

---

## 2. Satellite Constellation Matrix & Sensor Roles

| Constellation | Sensor Instrument | Spatial Resolution | Orbit & Overpass Time | Spectral Bands Used | Role in REACT-X |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NOAA-20 (JPSS-1)** | VIIRS | 375m (I-Bands) | Sun-synchronous (~13:30 LT ascending) | I4 (3.74μm MWIR), I5 (11.45μm TIR), M13 (4.05μm) | Primary Real-Time Detection |
| **NOAA-21 (JPSS-2)** | VIIRS | 375m (I-Bands) | Sun-synchronous (~13:30 LT ascending, 50-min orbit separation) | I4 (3.74μm MWIR), I5 (11.45μm TIR), M13 (4.05μm) | Primary Real-Time Detection |
| **Suomi-NPP** | VIIRS | 375m (I-Bands) | Sun-synchronous (~13:30 LT ascending) | I4, I5, M10-M16 (Nightfire physical retrieval) | Primary Detection & Nocturnal Characterization |
| **Terra / Aqua** | MODIS | 1,000m | Sun-synchronous (10:30 / 13:30 LT) | Band 21/22 (4.0μm), Band 31 (11.0μm) | Wide-Area Long-Term Baseline Cross-Check |
| **Sentinel-2A/B** | MSI | 20m (SWIR) | Sun-synchronous (5-day revisit) | Band 11 (1.61μm), Band 12 (2.19μm) | High-Resolution Structural & Smoke Confirmation |
| **Landsat 8/9** | TIRS-2 / OLI-2 | 100m (TIRS) / 30m (SWIR) | Sun-synchronous (8-day revisit with 8+9) | Band 10 (10.9μm Thermal Radiance) | High-Resolution Surface Temperature Verification |
| **INSAT-3D/3DR/3DS** | Imager / Sounder | 4,000m (TIR) | Geostationary (82°E, 15-min scan cycle) | TIR-1 (10.8μm), MIR (3.9μm) | Rapid Continuous Regional India Context *(Access Pending)* |

---

## 3. Dynamic Corroboration Agreement Formula

For a thermal source $S$ with linked observation set $\mathcal{O}_S$:

$$\text{Satellite Count } N_{\text{sat}} = |\text{Unique Satellites in } \mathcal{O}_S|$$

$$\text{Corroboration Confidence } C_{\text{corrob}} = \min\left(1.0, 0.40 + 0.25 \cdot (N_{\text{sat}} - 1) + 0.15 \cdot \mathbb{I}_{\text{multi-sensor}} + 0.10 \cdot \mathbb{I}_{\text{optical-confirmed}}\right)$$

Where:
- Single pass without corroboration: $C_{\text{corrob}} = 0.40$ (Flagged as `SINGLE-SATELLITE`).
- Dual pass (e.g. NOAA-20 + NOAA-21 within 6 hours): $C_{\text{corrob}} = 0.65$ (Flagged as `MULTI-SATELLITE`).
- Multi-satellite + High-resolution SWIR/TIRS confirmation: $C_{\text{corrob}} = 0.90 - 1.00$ (Flagged as `MULTI-SENSOR CONFIRMED`).

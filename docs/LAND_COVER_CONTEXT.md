# REACT-X Land-Cover Context Specification

**Document Version:** 1.0.0  
**Phase:** 17 — Advanced Thermal-Source Discrimination, Land-Cover Context & High-Resolution EO Verification  

---

## 1. Authoritative Datasets & Resolution

REACT-X integrates authoritative **10m-resolution global land cover** derived from ESA WorldCover and Copernicus Global Land Service.

### Supported Classes:
1. `INDUSTRIAL_BUILT_UP`: Industrial plants, petrochemical complexes, port terminals, tank farms.
2. `AGRICULTURE_CROPLAND`: Intensively cultivated agricultural fields and stubble burn regions.
3. `FOREST`: Deciduous, evergreen, and mangrove forest canopies.
4. `MINING_QUARRY`: Open-cast mines, overburden dumps, and smelting quarries.
5. `SETTLEMENT_URBAN`: High-density urban and residential fabric.
6. `SHRUBLAND_GRASSLAND`: Semi-arid scrubland and grasslands.
7. `BARE_GROUND_DESERT`: Sandy/rocky barren soils.
8. `WATER_BODIES`: Coastal waters, estuaries, and inland reservoirs.
9. `WETLANDS`: Mangroves and salt marshes.
10. `LAND_COVER_UNAVAILABLE`: Coordinates outside coverage boundary.

---

## 2. Land-Cover as Evidence, Not Hard Rules

> [!NOTE]
> Land cover provides environmental prior probability, but **never acts as an isolated decision gate**:
> - `INDUSTRIAL_BUILT_UP` $\ne$ automatically `INDUSTRIAL_FIRE` (most are routine flares or process units).
> - `FOREST` $\ne$ automatically `WILDFIRE_NATURAL` (could be localized campfires or illegal charcoal kilns).
>
> The classification emerges jointly from:
> $$\text{Evidence} = \text{Land Cover} + \text{Thermal Fingerprint} + \text{Diurnal Ratio} + \text{Facility Geometry} + \text{EO Verification}$$

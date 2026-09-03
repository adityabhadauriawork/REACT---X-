# SIH26162 — Canonical Thermal Data Foundation Architecture

**Organization:** National Technical Research Organisation (NTRO)  
**Product:** REACT-X / SIH26162 Industrial Thermal Intelligence & Emergency Response Platform  
**Document Version:** 1.0 (Phase 3 Foundation)

---

## 1. System Overview & Data Flow Pipeline

The SIH26162 data pipeline ingests raw spaceborne thermal observations, validates physical bounds, normalizes nomenclature and coordinate reference frames, computes deterministic deduplication keys and spatial H3 hexagonal indices, persists canonical records to indexed relational/spatial storage, and exposes filtered APIs and map-ready GeoJSON features for operational GIS display.

```
+---------------------------------------------------------------------------------------------------+
|                                 SPACEBORNE SENSOR CONSTELLATION                                   |
|   NASA FIRMS VIIRS (NOAA-20, NOAA-21, S-NPP)  |  NASA FIRMS MODIS (Terra, Aqua)  |  INSAT-3DR TIR  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v  [Raw CSV / JSON Telemetry Payload]
+---------------------------------------------------------------------------------------------------+
|                            PHASE 3: CANONICAL DATA FOUNDATION PIPELINE                            |
+---------------------------------------------------------------------------------------------------+
| 1. PARSING & INGESTION ADAPTER (`firms_service.py`)                                               |
|    - Column mapping for VIIRS 375m (I-band) and MODIS 1km products                                |
|    - UTC Timestamp parsing & ISO-8601 synchronization                                             |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 2. VALIDATION & QUALITY ASSURANCE ENGINE                                                          |
|    - Coordinate bounding: Latitude in [-90, 90], Longitude in [-180, 180]                         |
|    - Physical bounds: FRP >= 0.0 MW, Brightness Temp in [150K, 2500K]                             |
|    - Quality classification: [GOOD, WARNING, INVALID, DUPLICATE, STALE]                           |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 3. NORMALIZATION & CANONICAL MAPPING                                                              |
|    - Satellite naming: 'N' -> 'NOAA-20', 'NPP' -> 'SUOMI-NPP', 'T' -> 'TERRA', 'A' -> 'AQUA'      |
|    - Sensor naming: 'VIIRS_375M', 'MODIS_1KM', 'TIR_4KM'                                         |
|    - Confidence categorization: 'LOW' (<30%), 'NOMINAL' (30-79%), 'HIGH' (>=80%)                  |
|    - Day/Night pass: 'D' / 'N'                                                                    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 4. DETERMINISTIC DEDUPLICATION & SPATIAL H3 INDEXING                                              |
|    - Deduplication Key: SHA256(satellite:sensor:epoch_sec:round(lat,4):round(lon,4):round(frp,2))|
|    - Spatial Indexing: Uber H3 Resolution 7 (~1.22 km hexagonal cell aperture)                    |
|    - GeoJSON Point geometry: {"type": "Point", "coordinates": [lon, lat]}                         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 5. PERSISTENT STORAGE LAYER (`thermal_events` table)                                              |
|    - Relational SQLAlchemy Model with composite indexes:                                          |
|      * idx_thermal_lat_lon (latitude, longitude)                                                  |
|      * idx_thermal_acq_sat (acquisition_timestamp, source_satellite)                              |
|      * idx_thermal_h3_time (h3_index, acquisition_timestamp)                                      |
|      * idx_thermal_quality (data_quality_status, is_live_data)                                     |
|    - PostgreSQL + PostGIS compatible (SQLite memory/file development fallback)                    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 6. QUERY & DISPATCH APIS (`/api/thermal/*`)                                                       |
|    ├── GET  /api/thermal/events          (Filtered query: time, bbox, sat, confidence, status)    |
|    ├── GET  /api/thermal/events/{id}     (Single-event canonical radiometric detail)              |
|    ├── GET  /api/thermal/events/geojson  (Compact Map-Ready FeatureCollection for Leaflet GIS)    |
|    ├── GET  /api/thermal/stats           (KPI distributions, max FRP, live vs demo counts)        |
|    └── POST /api/thermal/ingest/firms    (Batch ingestion with deduplication & QA report)         |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Canonical Thermal Event Schema (`CanonicalThermalEvent`)

Every thermal observation ingested into the platform adheres strictly to the following specification:

| Field Name | Type | Constraints / Format | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | `String` | Primary Key, `FIRMS-{SAT}-{YYYYMMDDHHMM}-{HASH}` | Deterministic unique anomaly identifier |
| `dedup_key` | `String` | Unique SHA-256 Hash | Deduplication key preventing redundant records |
| `source` | `String` | Default: `NASA_FIRMS` | Data provider origin |
| `source_satellite` | `String` | `NOAA-20`, `NOAA-21`, `SUOMI-NPP`, `TERRA`, `AQUA` | Normalized spacecraft platform |
| `sensor_name` | `String` | `VIIRS_375M`, `MODIS_1KM`, `MSI_20M`, `TIR_4KM` | Normalized instrument descriptor |
| `source_version` | `String` | e.g. `v1.0NRT`, `Collection 6` | Instrument product version |
| `acquisition_timestamp` | `DateTime` | UTC ISO-8601 | Exact satellite overpass observation timestamp |
| `latitude` | `Float` | $-90.0 \le \text{lat} \le 90.0$ | WGS84 Geodetic Latitude |
| `longitude` | `Float` | $-180.0 \le \text{lon} \le 180.0$ | WGS84 Geodetic Longitude |
| `frp_mw` | `Float` | $\ge 0.0$ MW | Fire Radiative Power in Megawatts |
| `brightness_temp_k` | `Float` | $150.0 \le T_B \le 2500.0$ K | 4µm / 11µm brightness temperature in Kelvin |
| `brightness_temp_i4_k` | `Float` | Optional Kelvin | VIIRS I-band (375m) brightness temperature |
| `confidence` | `String` | `LOW`, `NOMINAL`, `HIGH` | Standardized categorical detection confidence |
| `confidence_pct` | `Float` | $0.0 \le \text{pct} \le 100.0$ | Continuous confidence percentage |
| `day_night` | `String` | `D` (Day), `N` (Night) | Diurnal solar illumination flag |
| `scan` | `Float` | Optional (km) | Along-scan ground pixel resolution |
| `track` | `Float` | Optional (km) | Along-track ground pixel resolution |
| `ingested_at` | `DateTime` | UTC ISO-8601 | System ingestion timestamp |
| `is_live_data` | `Boolean` | `True` (Live), `False` (Demo) | Distinguishes real telemetry from test scenarios |
| `data_quality_status` | `String` | `GOOD`, `WARNING`, `INVALID`, `DUPLICATE` | Explicit QA assessment flag |
| `data_quality_flags` | `List[String]` | e.g. `SUSPECT_LOW_TEMP`, `CLAMPED_FRP` | List of non-fatal quality warnings |
| `h3_index` | `String` | Resolution 7 Hexagon | Spatial aggregation cell index |
| `geometry` | `GeoJSON` | `{"type": "Point", "coordinates": [lon, lat]}` | Map-ready geometry object |
| `processing_status` | `String` | `RAW`, `NORMALIZED`, `ATTRIBUTED`, `VALIDATED` | Pipeline lifecycle stage |

### Future Phase Extension Hooks (Nullable / Default Pending)
The schema reserves typed slots for subsequent pipeline stages without requiring database schema rewrites:
- `classification`: Target 7-class taxonomy (`INDUSTRIAL_FIRE`, `GAS_FLARE`, `ROUTINE_PROCESS_HEAT`, `MINING_PROCESS_HEAT`, `AGRICULTURAL_BURNING`, `WILDFIRE_NATURAL`, `OTHER_UNKNOWN`)
- `classification_confidence`: Model probability ($0.0 \dots 1.0$)
- `persistence_category`: Recurrence status (`EXPECTED_PERSISTENT`, `ABNORMAL_PERSISTENT`, `TRANSIENT`, `NATURAL_NON_INDUSTRIAL`)
- `abnormality_score`: Statistical z-score departure percentage ($0.0 \dots 100.0$)
- `attributed_facility_id`: Matched OSM/GEM industrial complex identifier
- `facility_distance_m`: Distance to nearest plant perimeter boundary
- `nightfire_temp_k`: Planck curve fitted blackbody temperature ($K$)

---

## 3. Data Validation & Quality Rules

1. **Coordinate Integrity**:
   Records with $\text{latitude} \notin [-90, 90]$ or $\text{longitude} \notin [-180, 180]$ are marked `INVALID` and rejected from database insertion with `MALFORMED_COORDINATES`.
2. **FRP Bounds & Clamping**:
   Negative FRP values are clamped to $0.0\text{ MW}$ with a `WARNING` status and `NEGATIVE_FRP_CLAMPED` flag. Extreme FRP spikes ($> 5000\text{ MW}$) receive an `EXTREME_FRP_SPIKE` flag.
3. **Radiometric Temperature**:
   Brightness temperatures $< 200\text{ K}$ flag `SUSPECT_LOW_BRIGHTNESS_TEMP`; $> 2000\text{ K}$ flag `EXTREME_BRIGHTNESS_TEMP`.
4. **Time Invariants**:
   Observations with future timestamps ($> T_{\text{now}} + 10\text{ min}$) flag `FUTURE_TIMESTAMP_DETECTED`.

---

## 4. Deterministic Deduplication Algorithm

Deduplication does not rely solely on coordinate equality, as multiple satellites can observe the same hotspot or repeated scans may occur.

$$\text{DedupKey} = \text{SHA256}\left(\text{satellite} : \text{sensor} : \text{timestamp}_{\text{epoch}} : \text{round}(\text{lat}, 4) : \text{round}(\text{lon}, 4) : \text{round}(\text{frp}, 2)\right)$$

- **Spatial Resolution**: $\text{round}(\text{lat}, 4)$ provides $\sim 11.1\text{ meters}$ precision.
- **Temporal Resolution**: Integer epoch seconds.
- **Radiometric Resolution**: Two decimal places on Fire Radiative Power ($\text{MW}$).

When an incoming observation produces an identical SHA-256 hash to an existing database or batch record, it is marked `DUPLICATE` and skipped from storage while incrementing the `duplicates_skipped` telemetry metric.

---

## 5. Spatial Indexing & H3 Resolution Strategy

- **Resolution 7**:
  - Hexagon edge length: $\approx 1.22\text{ km}$
  - Cell area: $\approx 5.16\text{ km}^2$
  - Purpose: Groups individual $375\text{m}$ VIIRS pixels and $1\text{km}$ MODIS pixels into industrial complex clusters (e.g. Dahej PCPIR, Jamnagar Refinery, Hazira).
- **PostGIS Indexing**:
  - Relational indexes on `(latitude, longitude)`, `(acquisition_timestamp, source_satellite)`, and `(h3_index, acquisition_timestamp)` ensure spatial bounding-box and time-window queries execute in $< 10\text{ ms}$.

---

## 6. API Reference

### `GET /api/thermal/events`
Query canonical thermal events with multi-criteria filtering:
- `satellite`: `NOAA-20`, `NOAA-21`, `SUOMI-NPP`, `TERRA`, `AQUA`
- `confidence`: `LOW`, `NOMINAL`, `HIGH`
- `day_night`: `D`, `N`
- `is_live_data`: `true` (live), `false` (demo)
- `start_time` / `end_time`: ISO-8601 temporal range
- `min_lon`, `min_lat`, `max_lon`, `max_lat`: Bounding box
- `limit`, `offset`: Pagination parameters

### `GET /api/thermal/events/geojson`
Returns an RFC 7946 compliant GeoJSON `FeatureCollection` with lightweight properties (`event_id`, `frp_mw`, `brightness_temp_k`, `confidence`, `satellite`, `classification`, `abnormality_score`) ready for Leaflet and Mapbox GIS rendering.

### `GET /api/thermal/stats`
Returns system KPIs: total event count, live vs demo counts, breakdown by satellite constellation, day/night pass ratio, max observed FRP, and temporal span.

### `POST /api/thermal/ingest/firms`
Batch ingestion endpoint accepting raw or pre-structured NASA FIRMS records, returning an ingestion audit summary (`records_received`, `records_parsed`, `duplicates_skipped`, `records_persisted`, `quality_summary`).

# SIH26162 — Production NASA FIRMS Integration Guide

**Organization:** National Technical Research Organisation (NTRO)  
**Product:** REACT-X / SIH26162 Industrial Thermal Intelligence & Emergency Response Platform  
**Document Version:** 1.0 (Phase 4 Production Implementation)

---

## 1. System Architecture & NASA FIRMS Ingestion Pipeline

The SIH26162 platform ingests real-time spaceborne active-fire and thermal anomaly observations directly from the official **NASA FIRMS (Fire Information for Resource Management System) REST API**.

```
+---------------------------------------------------------------------------------------------------+
|                                      NASA FIRMS DATA SERVERS                                      |
|                       https://firms.modaps.eosdis.nasa.gov/api/area/csv                           |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼  [Authenticated HTTPS Request with MAP_KEY]
+---------------------------------------------------------------------------------------------------+
| 1. PRODUCTION INGESTION SERVICE (`firms_ingestion_service.py`)                                    |
|    - Multi-Constellation Poll: VIIRS NOAA-20, NOAA-21, Suomi-NPP (375m) & MODIS Terra, Aqua (1km)|
|    - Fault Tolerance: Exponential Backoff (3 retries), Rate-Limit (HTTP 429) & Timeout (15s) Guard |
|    - Stream Parsing: csv.DictReader with schema adaptation for VIIRS and MODIS formats            |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 2. QUALITY ASSURANCE & NORMALIZATION ENGINE (`firms_service.py`)                                  |
|    - Strict Range Validation: Latitude [-90, +90], Longitude [-180, +180], FRP >= 0 MW           |
|    - Quality Status Classification: [GOOD, WARNING, INVALID, DUPLICATE, STALE]                    |
|    - Standardization: UTC ISO-8601 timestamps, categorical confidence (LOW, NOMINAL, HIGH)        |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 3. DETERMINISTIC DEDUPLICATION & SPATIAL H3 INDEXING                                              |
|    - SHA-256 Physics Key: Hash(satellite:sensor:epoch_sec:round(lat,4):round(lon,4):round(frp,2))|
|    - Hexagonal Index: Uber H3 Resolution 7 (~1.22 km aperture)                                    |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 4. PERSISTENT STORAGE & APIS                                                                      |
|    - PostgreSQL + PostGIS & SQLite compatible `thermal_events` table                              |
|    - Filtered REST Endpoints (`GET /api/thermal/events`, `GET /api/thermal/stats`)                |
|    - Map-Ready RFC 7946 GeoJSON FeatureCollection (`GET /api/thermal/events/geojson`)             |
|    - Observability & Health Status API (`GET /api/thermal/feed/status`)                           |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
| 5. REACT-X OPERATIONAL COMMAND MAP & TRIAGE HUD                                                   |
|    - Visual separation of LIVE NASA TELEMETRY (Cyan) vs SIMULATION BENCHMARK (Amber)              |
|    - Real-time data freshness, overpass time, Planck temperature, and 1-click emergency handoff   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. NASA API Setup & Credential Management

### Step 1: Obtain a NASA FIRMS MAP_KEY
1. Register for an official, free NASA Earthdata MAP_KEY at:  
   👉 **https://firms.modaps.eosdis.nasa.gov/api/map_key**
2. Check your registered email for the 32-character hexadecimal key (e.g., `a1b2c3d4e5f678901234567890abcdef`).

### Step 2: Environment Configuration
Copy `.env.example` to `.env` or export environment variables:
```bash
# NASA FIRMS API Credentials
NASA_FIRMS_MAP_KEY=YOUR_32_CHAR_MAP_KEY
NASA_FIRMS_BASE_URL=https://firms.modaps.eosdis.nasa.gov/api/area/csv

# Ingestion Polling Parameters
FIRMS_POLL_INTERVAL_MINUTES=15
FIRMS_TIMEOUT_SEC=15.0
FIRMS_MAX_RETRIES=3
FIRMS_LOOKBACK_DAYS=1

# Spatial Bounding Box Filter [min_lon, min_lat, max_lon, max_lat]
# Default: Gujarat Industrial PCPIR & Western Industrial Corridor
FIRMS_DEFAULT_BBOX=68.0,20.0,75.0,25.0

# Active Constellations
FIRMS_SOURCE_CONSTELLATIONS=VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT,VIIRS_SNPP_NRT,MODIS_NRT
```

### Security Rule
- `NASA_FIRMS_MAP_KEY` is loaded strictly server-side through `app.core.config.settings`.
- It is **never** printed in server logs (masked as `***MAP_KEY***`), never exposed in API responses, and never bundled into frontend assets.

---

## 3. NASA FIRMS URL Structure & Field Mappings

### Official URL Syntax
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{BBOX}/{DAYS}
```
*Example for Dahej / Gujarat PCPIR with NOAA-20 VIIRS (1-day lookback):*
`https://firms.modaps.eosdis.nasa.gov/api/area/csv/YOUR_KEY/VIIRS_NOAA20_NRT/68,20,75,25/1`

### Field Mapping to CanonicalThermalEvent
| NASA FIRMS Field | CanonicalThermalEvent Field | Normalization & Conversion Rule |
| :--- | :--- | :--- |
| `latitude` | `latitude` | Validated in $[-90.0, 90.0]$ |
| `longitude` | `longitude` | Validated in $[-180.0, 180.0]$ |
| `bright_ti4` / `brightness` | `brightness_temp_k` | Converted to Kelvin ($150\text{ K} \dots 2500\text{ K}$) |
| `bright_ti5` / `bright_t31` | `brightness_temp_i4_k` | I-band / T31 baseline Kelvin temperature |
| `frp` | `frp_mw` | Negative clamped to $0.0\text{ MW}$ (`WARNING`) |
| `acq_date` + `acq_time` | `acquisition_timestamp` | Combined into UTC `datetime` ISO-8601 object |
| `satellite` (`N`, `21`, `NPP`, `T`, `A`) | `source_satellite` | Normalized: `NOAA-20`, `NOAA-21`, `SUOMI-NPP`, `TERRA`, `AQUA` |
| `confidence` (`l`, `n`, `h` / $0..100$) | `confidence` & `confidence_pct` | Categorical: `LOW`, `NOMINAL`, `HIGH` & Float $0..100\%$ |
| `daynight` (`D`, `N`) | `day_night` | Standardized to `'D'` (Day) or `'N'` (Night) |
| `scan` / `track` | `scan` / `track` | Along-scan / along-track spatial resolution in km |
| `version` | `source_version` | e.g. `v1.0NRT`, `Collection 6.1` |
| *(computed)* | `dedup_key` | SHA-256 invariant hash |
| *(computed)* | `h3_index` | Uber H3 Resolution 7 hexagon index |
| *(flag)* | `is_live_data` | `True` for live FIRMS API, `False` for benchmark |

---

## 4. Resilience, Fault Tolerance & Deduplication

### 1. HTTP Error & Rate Limit Handling
- **HTTP 429 (Rate Limited)**: Reads `Retry-After` header and applies exponential backoff ($1\text{s} \rightarrow 2\text{s} \rightarrow 4\text{s}$).
- **HTTP 401 / 403 (Invalid Key)**: Logs descriptive security error, sets status to `DEGRADED` / `NO_KEY_CONFIGURED`, and avoids spamming NASA servers.
- **Timeouts**: Configured with strict $15\text{s}$ timeout; failures are recorded in `last_error` without backend crashes.

### 2. Overlapping Retrieval Window & Deterministic Deduplication
- Polls with an overlapping $24\text{h}$ lookback window.
- Duplicates are identified deterministically:
  $$\text{DedupKey} = \text{SHA256}\left(\text{satellite} : \text{sensor} : \text{epoch\_sec} : \text{round}(\text{lat}, 4) : \text{round}(\text{lon}, 4) : \text{round}(\text{frp}, 2)\right)$$
- If the key exists in the database, the record is marked `DUPLICATE`, skipped from insertion, and tallied under `duplicates_skipped_total`.

---

## 5. Live Telemetry & Observability API

### Feed Status Endpoint: `GET /api/thermal/feed/status`
Returns live diagnostic status:
```json
{
  "api_health_status": "HEALTHY",
  "has_configured_api_key": true,
  "configured_sources": [
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
    "MODIS_NRT"
  ],
  "poll_interval_minutes": 15,
  "default_bbox": "68.0,20.0,75.0,25.0",
  "last_poll_timestamp": "2026-08-30T09:30:00Z",
  "last_successful_poll_timestamp": "2026-08-30T09:30:00Z",
  "records_received_total": 420,
  "records_persisted_total": 380,
  "duplicates_skipped_total": 40,
  "records_rejected_total": 0,
  "last_error": null,
  "is_polling_active": true
}
```

### Manual Trigger Endpoint: `POST /api/thermal/feed/poll`
Triggers an immediate asynchronous synchronization cycle on-demand.

---

## 6. Data Honesty Rules

To maintain scientific and operational integrity:
1. **Raw FIRMS Hotspots**: Labeled strictly as **Thermal Anomaly / Active Fire Detection**.
2. **Pending Attribution**: If a detection has not yet undergone spatial KD-tree polygon matching, it is marked `Attribution: Pending Spatial KD-Tree Index`.
3. **Pending ML Classification**: If a detection has not yet passed through the 7-class classifier (Phase 7), the classification field displays `PENDING ML CLASSIFICATION`.
4. **Live vs Simulation Distinction**: Live NASA telemetry displays a glowing cyan badge (`LIVE NASA SATELLITE`), while synthetic test fixtures display an amber badge (`SIMULATION BENCHMARK`).

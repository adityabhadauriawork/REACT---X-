# REACT-X — Final Production Deployment & Operational Runbook

## 1. System Overview & Deployment Topology
REACT-X is an industrial-scale, multi-modal thermal intelligence and emergency response platform designed for continuous operations across Indian refineries, petrochemical corridors, and national disaster management centers.

```
 Internet / Enterprise Network
              ↓
    Nginx (Port 80 / 443)
              ↓
  FastAPI API Workers Pool (ENABLE_BACKGROUND_POLL=false)
              ↓
  PostgreSQL 16 + PostGIS 3.4 (Persistent Volume: reactx_pgdata)

              ▲
              │
  Dedicated Ingestion Worker Container (ENABLE_BACKGROUND_POLL=true)
              ↓
  NASA FIRMS / Public STAC Catalogs (AWS Earth Search & Planetary Computer)
```

---

## 2. Environment Configuration Matrix

| Variable Name | Classification | Default Value | Mandatory? | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_ENV` | `[REAL/LIVE]` | `production` | Yes | Environment mode (`production`, `reference`, `simulation`, `development`). Enforces Postgres and explicit CORS in production. |
| `DATABASE_URL` | `[REAL/LIVE]` | `postgresql://...` | Yes | PostgreSQL connection string. SQLite is strictly rejected in production. |
| `POSTGRES_PASSWORD` | `[REAL/LIVE]` | `None` | Yes | Secure password for PostgreSQL service container. |
| `NASA_FIRMS_MAP_KEY` | `[REAL/LIVE]` | `""` | Live Polling | 32-character NASA FIRMS map key for real-time VIIRS/MODIS satellite data. |
| `FIRMS_POLL_INTERVAL_MINUTES`| `[REAL/LIVE]` | `15` | No | Polling frequency for thermal anomaly scrapes (15m recommended). |
| `FIRMS_DEFAULT_BBOX` | `[REAL/LIVE]` | `68.0,8.0,97.0,37.5` | No | India-wide bounding box coordinates `[min_lon, min_lat, max_lon, max_lat]`. |
| `ENABLE_BACKGROUND_POLL` | `[REAL/LIVE]` | `false` | Yes | Must be `false` on API containers; set to `true` **only** on the dedicated worker. |
| `CORS_ORIGINS` | `[REAL/LIVE]` | Explicit URLs | Yes | Comma-separated allowed web origins. Wildcard `*` is prohibited in production. |
| `COPERNICUS_CLIENT_ID` | `[OPTIONAL]` | `""` | No | Copernicus CDSE OAuth client. Falls back to public AWS Earth Search STAC. |
| `USGS_M2M_USERNAME` | `[OPTIONAL]` | `""` | No | USGS Landsat M2M credentials. Falls back to Planetary Computer STAC. |
| `EOG_VNF_USERNAME` | `[OPTIONAL]` | `""` | No | Commercial VNF credentials. Native Planck blackbody estimator runs by default. |

---

## 3. Production Deployment Step-by-Step

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/adityabhadauriawork/SIH-1505-Industrial-Emergency-Response.git
cd SIH-1505
cp .env.example .env
# Edit .env and configure DATABASE_URL, POSTGRES_PASSWORD, CORS_ORIGINS, and NASA_FIRMS_MAP_KEY
```

### Step 2: Launch Deployment Stack via Docker Compose
```bash
docker compose up -d --build
```

### Step 3: Verify Service Health & Readiness
```bash
# Verify all containers are healthy
docker compose ps

# Check API readiness probe
curl -f http://localhost/readiness

# Check Prometheus metrics export
curl -s http://localhost/metrics | head -n 20
```

---

## 4. Database Setup & Initialization
- PostgreSQL 16 with PostGIS 3.4 is initialized automatically on first startup via `deploy/postgres/init-postgis.sql`.
- UTC timezone and UTF-8 encoding are enforced at container initialization.
- Automatic migrations and idempotent seed loading run on backend startup (`run_auto_migrations`).
- Persistent volume `reactx_pgdata` preserves spatial indices and historical partitions.

---

## 5. Ingestion Worker Guard & Scalability
In clustered deployments (e.g. 8 API containers behind Nginx):
- API containers are spawned with `ENABLE_BACKGROUND_POLL=false`.
- Exactly one `reactx_ingestion_worker` container runs with `ENABLE_BACKGROUND_POLL=true`.
- Guarantees zero redundant NASA FIRMS API requests and eliminates lock contention.

---

## 6. Observability, Metrics & Alerting

### Prometheus Scraping
Prometheus scrapes the API `/metrics` endpoint every 15 seconds on internal port 8000.

### Alert Rules Summary (`deploy/prometheus/alert_rules.yml`)
- `FirmsIngestionFailure`: Triggers when >2 FIRMS polling failures occur in 15m.
- `FirmsIngestionLag`: Triggers if no thermal data ingested for >45m.
- `ApiHighErrorRate`: Triggers if 5xx HTTP error rate exceeds 1% over 5m.
- `ApiHighLatencyP95`: Triggers if P95 request latency exceeds 500ms.
- `DatabaseUnavailable`: Triggers immediately if database connectivity check fails.
- `TelemetryConnectionDegraded`: Triggers if active SCADA/IoT protocol connections drop to zero.
- `ReactxServiceUnavailable`: Triggers if API web process is unresponsive.

### Grafana Dashboard
Access the pre-provisioned Operations Dashboard at `http://<host>:3001` (Default credentials: `admin` / `admin`).

---

## 7. Backup Strategy & Procedure

### Automated Backup Snapshot
```bash
python scripts/backup_db.py --keep-days 30
```
- Creates a timestamped, gzip-compressed snapshot in `backups/reactx_backup_YYYYMMDD_HHMMSSZ.dump` (or `.db.gz`).
- Computes SHA-256 verification hash and writes JSON manifest.
- Automatically purges backups older than 30 days.

### Database Restoration Procedure
```bash
python scripts/restore_db.py --file backups/reactx_backup_YYYYMMDD_HHMMSSZ.db.gz --target restored.db
```
- Validates SHA-256 checksum against manifest before applying changes.
- Validates database PRAGMA integrity check post-restoration.

---

## 8. Data Retention & Archival Policy (90-Day Rule)
```bash
python scripts/archive_retention.py --days 90
```
- **Archived**: Unlinked raw thermal detections and high-frequency telemetry older than 90 days are exported to compressed JSONL archives (`archives/archived_thermal_events_*.jsonl.gz`) and purged from the hot database.
- **Permanently Preserved**: Confirmed industrial fire incidents, emergency preplans, critical sensor alarm readings, and baseline facility fingerprints are **never** deleted.
- **Audit**: Every archival run logs an auditable entry to the decision audit trail.

---

## 9. Declarative Facility Onboarding
To onboard a new Indian refinery or chemical complex without modifying source code:
1. Create a declarative JSON configuration (see `data/onboarding_sample_paradip.json` for reference).
2. Execute the onboarding utility:
```bash
python scripts/onboard_facility.py --config data/onboarding_sample_paradip.json
```
3. The facility, units, assets, sensors, and preplans are registered immediately in spatial and telemetry registries.

---

## 10. Industrial Safety Boundary (Strict Read-Only Enforcement)
REACT-X operates strictly out-of-band and is non-invasive:
- **Zero Write Operations**: No write methods exist to PLC, DCS, SIS, ESD, Actuators, or Control Loops.
- **Isolation**: Physical and logical one-way data diodes or read-only OPC UA / Modbus polling ensures zero operational risk to plant processes.

---

## 11. Shutdown & Restart Procedure
```bash
# Graceful shutdown (sends SIGTERM to worker and API pool)
docker compose down

# Restart stack
docker compose restart
```

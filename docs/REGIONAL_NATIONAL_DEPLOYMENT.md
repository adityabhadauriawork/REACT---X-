# REACT-X — Regional & National Deployment Verification Guide

## 1. Architectural Overview
The REACT-X intelligence architecture (Planar thermal estimation, 7-class classifier, 23-feature vector, Dempster-Shafer evidence fusion, and non-invasive industrial safety boundary) is mathematically facility-agnostic and scales across three operational tiers without source code modification.

```
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 3: INDIA-WIDE NATIONAL COMMAND PLATFORM             │
│   (NDMA, MoPNG, Central EOC — Pan-India BBOX 68.0,8.0,97.0,37.5)       │
│                                                                        │
│   [Nginx Cluster] ──> [16+ FastAPI API Replicas] ──> [PostGIS HA Cluster]
│                             ▲                              │          │
│              [Dedicated Ingestion Worker]                  │          │
│          (NASA FIRMS, CDSE STAC, Planetary STAC)           │          │
└────────────────────────────────┬───────────────────────────┴──────────┘
                                 │ Replicated Telemetry / Edge Summaries
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 2: REGIONAL INDUSTRIAL CORRIDOR HUB                 │
│        (Dahej PCPIR, Jamnagar-Hazira, Paradip Industrial Zone)         │
│                                                                        │
│   [Nginx Proxy] ──> [4-8 FastAPI Replicas] ──> [Corridor PostGIS DB]   │
│                             ▲                                          │
│              [Corridor Ingestion Worker (Local BBOX)]                  │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ Zero-Trust Read-Only Gateway Link
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 1: SINGLE PLANT / EDGE DEPLOYMENT                   │
│         (Hazira Complex, Paradip Refinery, Jamnagar Refinery)          │
│                                                                        │
│   [Lightweight Nginx] ──> [1-2 FastAPI Workers] ──> [Local PostGIS DB] │
│   [Edge Ingestion Adapter (OPC UA / Modbus / MQTT)] [Read-Only Boundary]
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Tier Specification Matrix

| Operational Dimension | Tier 1: Single Plant / Edge | Tier 2: Regional Corridor | Tier 3: India-Wide National Platform |
| :--- | :--- | :--- | :--- |
| **Primary Use Case** | Plant HSE control room, local perimeter fire detection, onsite asset thermal health | Corridor industrial mutual aid, district disaster authority, inter-plant domino mitigation | Ministry of Petroleum & Natural Gas, NDMA, National EOC, national thermal surveillance |
| **Database Architecture** | Standalone PostgreSQL 16 + PostGIS (or embedded SQLite for edge field units) | PostgreSQL 16 + PostGIS cluster with 1 primary + 1 synchronous read replica | Multi-AZ High-Availability PostgreSQL 16 + PostGIS cluster with connection poolers (PgBouncer) |
| **FastAPI API Workers** | 1–2 worker processes (`ENABLE_BACKGROUND_POLL=false`) | 4–8 worker processes across 2 container instances | 16–32 horizontally scaled stateless API workers behind Nginx load balancers |
| **Satellite Ingestion Worker**| Optional (can consume pre-filtered events from Regional Hub or poll local bounding box) | 1 Dedicated Worker container (`ENABLE_BACKGROUND_POLL=true`, local corridor BBOX e.g. 50km radius) | 1 Dedicated Master Worker container (`ENABLE_BACKGROUND_POLL=true`, India BBOX `68.0,8.0,97.0,37.5`) |
| **Facility Registry Scope** | Single plant hierarchy (1 facility, 10–50 assets, 100–500 tags) | Regional corridor (10–50 facilities, 500–2,000 assets, 10,000+ tags) | Pan-India registry (500+ refineries, petrochemical complexes, thermal plants, mining sites) |
| **Industrial Telemetry** | Direct plant LAN / OT gateway links (OPC UA, Modbus TCP, MQTT broker) — strictly READ-ONLY | Aggregated corridor edge gateways via encrypted IPSec/WireGuard tunnels | Summarized regional status streams and critical alarm feeds |
| **Observability & Monitoring** | Local Prometheus container + Grafana dashboard | Prometheus + Alertmanager with SMS/Email/Telegram dispatch to District Officers | Centralized Prometheus / Thanos / Grafana cluster with 24x7 EOC alerting |
| **Intelligence Engine Code** | **100% IDENTICAL (Frozen)** | **100% IDENTICAL (Frozen)** | **100% IDENTICAL (Frozen)** |

---

## 3. Deployment Configuration Per Tier

### Tier 1 (Single Plant / Edge `.env`):
```env
APP_ENV=production
DATABASE_URL=postgresql://reactx:SECRET@localhost:5432/reactx_plant
FIRMS_DEFAULT_BBOX=72.50,21.05,72.85,21.30
ENABLE_BACKGROUND_POLL=true
CORS_ORIGINS=https://hse-control.plant.internal
```

### Tier 2 (Regional Corridor `.env`):
```env
APP_ENV=production
DATABASE_URL=postgresql://reactx:SECRET@corridor-db-cluster:5432/reactx_corridor
FIRMS_DEFAULT_BBOX=72.00,20.50,73.50,22.50
ENABLE_BACKGROUND_POLL=false  # Set to true only on dedicated worker
CORS_ORIGINS=https://corridor-eoc.gujarat.gov.in,https://command.dahej.internal
```

### Tier 3 (India-Wide National Command `.env`):
```env
APP_ENV=production
DATABASE_URL=postgresql://reactx_admin:STRONG_SECRET@national-db-pooler:5432/reactx_national
FIRMS_DEFAULT_BBOX=68.0,8.0,97.0,37.5
ENABLE_BACKGROUND_POLL=false  # Set to true only on dedicated worker container
CORS_ORIGINS=https://reactx.ndma.gov.in,https://command.mopng.gov.in
```

---

## 4. Operational Invariant
Across all tiers, the scientific core remains uncompromised:
- 7-Class HistGradientBoosting Calibrated Classifier
- 23-Feature Non-Parametric Feature Vector
- Zero-auth AWS Earth Search & Planetary Computer STAC
- Multimodal Dempster-Shafer Evidence Accumulator
- Strict Read-Only Industrial Isolation Boundary
